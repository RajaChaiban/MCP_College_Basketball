"""ESPN hidden API adapter."""

import structlog

from cbb_mcp.models.common import Record, Venue
from cbb_mcp.models.games import (
    BoxScore,
    Game,
    Play,
    PlayerBoxScore,
    PlayByPlay,
    TeamBoxScore,
    TeamScore,
)
from cbb_mcp.models.rankings import (
    ConferenceStandings,
    Poll,
    RankedTeam,
    StandingsEntry,
)
from cbb_mcp.models.stats import PlayerStats, StatLeader, TeamStats
from cbb_mcp.models.teams import Player, Team
from cbb_mcp.sources.base import DataCapability, DataSource
from cbb_mcp.utils.constants import (
    CURRENT_SEASON,
    ESPN_API_BASE,
    ESPN_CONFERENCES,
    ESPN_CORE_BASE,
    ESPN_WEB_BASE,
)
from cbb_mcp.utils.errors import GameNotFoundError, SourceError, TeamNotFoundError
from cbb_mcp.utils.http_client import fetch_json

logger = structlog.get_logger()

# ESPN's scoreboard returns a `conferenceId` per team that differs from
# the `groups` param used in the scoreboard URL.  This maps the
# user-friendly conference name → scoreboard conferenceId.
# Verified by looking up known teams via the /teams/{id} endpoint.
_SCOREBOARD_CONF_IDS: dict[str, str] = {
    "ACC": "2",
    "Big 12": "8",
    "Big East": "4",
    "Big Ten": "7",
    "SEC": "23",
    "WCC": "29",
    "A-10": "3",
    "Mountain West": "44",
    "Ivy": "12",
    "MAAC": "13",
    "C-USA": "11",
    "ASUN": "11",
    "Big West": "9",
    "Horizon": "45",
}


def _safe_get(data: dict, *keys, default=""):
    """Safely traverse nested dicts."""
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key, {})
        elif isinstance(current, list) and isinstance(key, int) and key < len(current):
            current = current[key]
        else:
            return default
    return current if current != {} else default


class ESPNSource(DataSource):
    name = "espn"
    priority = 1

    def capabilities(self) -> set[DataCapability]:
        return {
            DataCapability.LIVE_SCORES,
            DataCapability.TEAM_INFO,
            DataCapability.TEAM_SEARCH,
            DataCapability.ROSTER,
            DataCapability.SCHEDULE,
            DataCapability.GAME_DETAIL,
            DataCapability.BOX_SCORE,
            DataCapability.PLAY_BY_PLAY,
            DataCapability.RANKINGS,
            DataCapability.STANDINGS,
            DataCapability.TEAM_STATS,
            DataCapability.PLAYER_STATS,
            DataCapability.STAT_LEADERS,
        }

    # ── Scores ──────────────────────────────────────────────────

    async def get_live_scores(
        self, date: str, conference: str = "", top25: bool = False
    ) -> list[Game]:
        # Always fetch all games — ESPN's server-side 'groups' filter is
        # unreliable and can return teams from the wrong conference.
        params: dict[str, str] = {"dates": date.replace("-", ""), "limit": "200"}

        try:
            data = await fetch_json(f"{ESPN_API_BASE}/scoreboard", params=params)
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch scores: {e}") from e

        # Resolve the target conference ID from scoreboard data for filtering.
        # ESPN scoreboard competitors include a `conferenceId` field that we
        # can match against the conference name.
        target_conf_id: str | None = None
        if conference:
            target_conf_id = await self._find_conference_id(data, conference)

        games: list[Game] = []
        for event in data.get("events", []):
            if target_conf_id is not None:
                if not self._event_has_conference(event, target_conf_id):
                    continue
            game = self._parse_event(event)
            if top25 and not (game.home.rank or game.away.rank):
                continue
            games.append(game)
        return games

    async def _find_conference_id(self, scoreboard_data: dict, conference: str) -> str | None:
        """Look up the ESPN conferenceId for a given conference name.

        ESPN's scoreboard embeds a conferenceId on each competitor's team
        object, but it uses a different numbering system than the URL
        ``groups`` parameter. We first check a static map of known IDs,
        then fall back to a dynamic lookup.
        """
        if conference not in ESPN_CONFERENCES:
            return None

        # Fast path: static map covers major conferences
        if conference in _SCOREBOARD_CONF_IDS:
            return _SCOREBOARD_CONF_IDS[conference]

        # Slow path: find a team from this conference via search,
        # then look up its groups.id from the team detail endpoint.
        try:
            teams_data = await fetch_json(
                f"{ESPN_API_BASE}/teams", params={"limit": "400"}
            )
            all_teams = (
                teams_data.get("sports", [{}])[0]
                .get("leagues", [{}])[0]
                .get("teams", [])
            )
            # Pick the first team, look up its detail to get groups.id
            if all_teams:
                sample_id = str(all_teams[0].get("team", all_teams[0]).get("id", ""))
                if sample_id:
                    detail = await fetch_json(f"{ESPN_API_BASE}/teams/{sample_id}")
                    team = detail.get("team", detail)
                    gid = str(team.get("groups", {}).get("id", ""))
                    if gid:
                        # Cache for future calls
                        _SCOREBOARD_CONF_IDS[conference] = gid
                        return gid
        except Exception:
            logger.debug("conference_id_lookup_failed", conference=conference)

        return None

    @staticmethod
    def _event_has_conference(event: dict, conf_id: str) -> bool:
        """Check if any team in an event belongs to the given conferenceId."""
        comp = event.get("competitions", [{}])[0]
        for c in comp.get("competitors", []):
            if str(c.get("team", {}).get("conferenceId", "")) == conf_id:
                return True
        return False

    # ── Teams ───────────────────────────────────────────────────

    async def get_team(self, team_id: str) -> Team:
        try:
            data = await fetch_json(f"{ESPN_API_BASE}/teams/{team_id}")
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch team {team_id}: {e}") from e

        team_data = data.get("team", data)
        if not team_data or not team_data.get("id"):
            raise TeamNotFoundError(team_id)
        return self._parse_team(team_data)

    async def search_teams(self, query: str, conference: str = "") -> list[Team]:
        try:
            data = await fetch_json(
                f"{ESPN_API_BASE}/teams", params={"limit": "400"}
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to search teams: {e}") from e

        teams: list[Team] = []
        query_lower = query.lower()
        for t in data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", []):
            team_data = t.get("team", t)
            name = team_data.get("displayName", "").lower()
            abbr = team_data.get("abbreviation", "").lower()
            nickname = team_data.get("nickname", "").lower()
            location = team_data.get("location", "").lower()

            if query_lower in name or query_lower in abbr or query_lower in nickname or query_lower in location:
                team = self._parse_team(team_data)
                if conference and team.conference.lower() != conference.lower():
                    continue
                teams.append(team)
        return teams

    async def get_roster(self, team_id: str) -> list[Player]:
        try:
            data = await fetch_json(
                f"{ESPN_API_BASE}/teams/{team_id}/roster"
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch roster: {e}") from e

        players: list[Player] = []
        athletes_data = data.get("athletes", [])

        for entry in athletes_data:
            # Handle both flat array and grouped {items: [...]} formats
            if isinstance(entry, dict) and "items" in entry:
                athlete_list = entry["items"]
            elif isinstance(entry, dict) and "displayName" in entry:
                athlete_list = [entry]
            else:
                continue

            for athlete in athlete_list:
                players.append(
                    Player(
                        id=str(athlete.get("id", "")),
                        name=athlete.get("displayName", ""),
                        jersey=athlete.get("jersey", ""),
                        position=_safe_get(athlete, "position", "abbreviation"),
                        height=athlete.get("displayHeight", ""),
                        weight=str(athlete.get("displayWeight", "")),
                        year=_safe_get(athlete, "experience", "displayValue"),
                        hometown=_safe_get(athlete, "birthPlace", "city"),
                    )
                )
        return players

    async def get_schedule(self, team_id: str, season: int = 0) -> list[Game]:
        season = season or CURRENT_SEASON
        try:
            data = await fetch_json(
                f"{ESPN_API_BASE}/teams/{team_id}/schedule",
                params={"season": str(season)},
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch schedule: {e}") from e

        games: list[Game] = []
        for event in data.get("events", []):
            games.append(self._parse_event(event))
        return games

    # ── Game Detail / Box Score ─────────────────────────────────

    async def get_game_detail(self, game_id: str) -> Game:
        try:
            data = await fetch_json(
                f"{ESPN_API_BASE}/summary", params={"event": game_id}
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch game {game_id}: {e}") from e

        header = data.get("header", {})
        competitions = header.get("competitions", [{}])
        if not competitions:
            raise GameNotFoundError(game_id)
        return self._parse_summary_header(header, competitions[0])

    async def get_box_score(self, game_id: str) -> BoxScore:
        try:
            data = await fetch_json(
                f"{ESPN_API_BASE}/summary", params={"event": game_id}
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch box score: {e}") from e

        header = data.get("header", {})
        competitions = header.get("competitions", [{}])
        if not competitions:
            raise GameNotFoundError(game_id)

        game = self._parse_summary_header(header, competitions[0])
        box = BoxScore(game=game)

        box_data = data.get("boxscore", {})
        players_list = box_data.get("players", [])

        for i, team_box in enumerate(players_list):
            team_box_score = self._parse_team_box(team_box)
            if i == 0:
                box.away = team_box_score
            else:
                box.home = team_box_score

        return box

    async def get_play_by_play(self, game_id: str) -> PlayByPlay:
        try:
            data = await fetch_json(
                f"{ESPN_API_BASE}/summary", params={"event": game_id}
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch PBP: {e}") from e

        header = data.get("header", {})
        competitions = header.get("competitions", [{}])
        if not competitions:
            raise GameNotFoundError(game_id)

        game = self._parse_summary_header(header, competitions[0])
        plays_data = data.get("plays", [])
        plays: list[Play] = []

        for seq, p in enumerate(plays_data):
            play = Play(
                id=str(p.get("id", "")),
                sequence=seq,
                period=p.get("period", {}).get("number", 0),
                clock=p.get("clock", {}).get("displayValue", ""),
                description=p.get("text", ""),
                team_id=str(p.get("team", {}).get("id", "")),
                score_home=p.get("homeScore", 0),
                score_away=p.get("awayScore", 0),
                scoring_play=p.get("scoringPlay", False),
                shot_type=p.get("type", {}).get("text", ""),
            )
            coord = p.get("coordinate", {})
            if coord:
                play.coordinate_x = coord.get("x")
                play.coordinate_y = coord.get("y")
            plays.append(play)

        return PlayByPlay(game=game, plays=plays)

    # ── Rankings ────────────────────────────────────────────────

    async def get_rankings(
        self, poll_type: str = "ap", season: int = 0, week: int = 0
    ) -> Poll:
        season = season or CURRENT_SEASON
        params: dict[str, str] = {"season": str(season)}
        if week:
            params["week"] = str(week)

        try:
            data = await fetch_json(f"{ESPN_API_BASE}/rankings", params=params)
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch rankings: {e}") from e

        poll_map = {"ap": 0, "coaches": 1}
        poll_idx = poll_map.get(poll_type.lower(), 0)

        rankings_list = data.get("rankings", [])
        if not rankings_list:
            return Poll(name=poll_type, season=season, teams=[])

        if poll_idx >= len(rankings_list):
            poll_idx = 0

        poll_data = rankings_list[poll_idx]
        ranked_teams: list[RankedTeam] = []

        for entry in poll_data.get("ranks", []):
            team_data = entry.get("team", {})
            prev = entry.get("previous", 0)
            current = entry.get("current", 0)

            if prev == 0:
                trend = "new"
            elif current < prev:
                trend = "up"
            elif current > prev:
                trend = "down"
            else:
                trend = "same"

            ranked_teams.append(
                RankedTeam(
                    rank=current,
                    team_id=str(team_data.get("id", "")),
                    team_name=team_data.get("nickname", team_data.get("name", "")),
                    conference=team_data.get("conference", ""),
                    record=entry.get("recordSummary", ""),
                    points=entry.get("points", 0),
                    previous_rank=prev,
                    trend=trend,
                )
            )

        return Poll(
            name=poll_data.get("name", poll_type),
            season=season,
            week=poll_data.get("week", week),
            date=poll_data.get("date", ""),
            teams=ranked_teams,
        )

    # ── Standings ───────────────────────────────────────────────

    async def get_standings(self, conference: str = "") -> list[ConferenceStandings]:
        params: dict[str, str] = {"season": str(CURRENT_SEASON)}
        if conference:
            conf = ESPN_CONFERENCES.get(conference)
            if conf:
                params["group"] = conf["id"]

        try:
            data = await fetch_json(
                f"{ESPN_WEB_BASE}/standings", params=params
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch standings: {e}") from e

        standings_list: list[ConferenceStandings] = []

        # The web API returns either a single conference (with standings
        # at top level) or multiple conferences under "children".
        conference_blocks: list[dict] = []
        if data.get("children"):
            conference_blocks = data["children"]
        elif data.get("standings"):
            # Single conference response
            conference_blocks = [data]

        for block in conference_blocks:
            conf_name = block.get("name", block.get("abbreviation", ""))
            entries: list[StandingsEntry] = []

            standings_entries = block.get("standings", {}).get("entries", [])
            for i, entry in enumerate(standings_entries):
                team_data = entry.get("team", {})
                # Build stat lookup keyed by "type" (unique per stat)
                stats_by_type: dict[str, str] = {}
                for s in entry.get("stats", []):
                    stype = s.get("type", "")
                    val = s.get("summary", s.get("displayValue", ""))
                    stats_by_type[stype] = val

                overall = stats_by_type.get("total", "")
                conf_record = stats_by_type.get("vsconf", "")
                streak_display = stats_by_type.get("streak", "")

                entries.append(
                    StandingsEntry(
                        team_id=str(team_data.get("id", "")),
                        team_name=team_data.get("displayName", ""),
                        conference_rank=i + 1,
                        overall_record=overall,
                        conference_record=conf_record,
                        streak=streak_display,
                    )
                )

            standings_list.append(
                ConferenceStandings(
                    conference=conf_name,
                    season=CURRENT_SEASON,
                    teams=entries,
                )
            )
        return standings_list

    # ── Stats ───────────────────────────────────────────────────

    async def get_team_stats(self, team_id: str, season: int = 0) -> TeamStats:
        season = season or CURRENT_SEASON
        try:
            data = await fetch_json(
                f"{ESPN_API_BASE}/teams/{team_id}/statistics",
                params={"season": str(season)},
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch team stats: {e}") from e

        stat_map: dict[str, float] = {}

        # ESPN site API nests stats under results.stats.categories
        categories = (
            data.get("results", {}).get("stats", {}).get("categories", [])
        )
        for category in categories:
            if isinstance(category, dict):
                for stat in category.get("stats", []):
                    name = stat.get("name", "")
                    try:
                        stat_map[name] = float(stat.get("value", 0))
                    except (ValueError, TypeError):
                        pass

        return TeamStats(
            team_id=team_id,
            team_name=data.get("team", {}).get("displayName", ""),
            season=season,
            games_played=int(stat_map.get("gamesPlayed", 0)),
            ppg=stat_map.get("avgPoints", stat_map.get("points", 0)),
            opp_ppg=stat_map.get("avgPointsAgainst", 0),
            fg_pct=stat_map.get("fieldGoalPct", 0),
            three_pct=stat_map.get("threePointFieldGoalPct", 0),
            ft_pct=stat_map.get("freeThrowPct", 0),
            rpg=stat_map.get("avgRebounds", stat_map.get("rebounds", 0)),
            offensive_rpg=stat_map.get("avgOffensiveRebounds", 0),
            defensive_rpg=stat_map.get("avgDefensiveRebounds", 0),
            apg=stat_map.get("avgAssists", stat_map.get("assists", 0)),
            spg=stat_map.get("avgSteals", stat_map.get("steals", 0)),
            bpg=stat_map.get("avgBlocks", stat_map.get("blocks", 0)),
            topg=stat_map.get("avgTurnovers", stat_map.get("turnovers", 0)),
        )

    async def get_player_stats(
        self, player_id: str = "", team_id: str = ""
    ) -> list[PlayerStats]:
        if not team_id:
            return []

        season = CURRENT_SEASON

        # Step 1: Get athlete refs from core API
        try:
            roster_data = await fetch_json(
                f"{ESPN_CORE_BASE}/seasons/{season}/teams/{team_id}/athletes",
                params={"limit": "50"},
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch athlete list: {e}") from e

        athlete_refs = [
            item["$ref"] for item in roster_data.get("items", [])
            if isinstance(item, dict) and "$ref" in item
        ]

        # Step 2: Fetch athlete profiles concurrently to get names/positions
        import asyncio
        athletes_info: list[dict] = []
        try:
            tasks = [fetch_json(ref) for ref in athlete_refs]
            athletes_info = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch athlete profiles: {e}") from e

        # Step 3: Fetch per-athlete season stats concurrently
        stat_refs = [
            f"{ESPN_CORE_BASE}/seasons/{season}/types/2/athletes/{a.get('id')}/statistics/0"
            for a in athletes_info
            if isinstance(a, dict) and a.get("id")
        ]
        stats_results: list = []
        try:
            tasks = [fetch_json(ref) for ref in stat_refs]
            stats_results = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            pass

        # Step 4: Combine athlete info with stats
        team_name = ""
        players: list[PlayerStats] = []
        for i, athlete_data in enumerate(athletes_info):
            if not isinstance(athlete_data, dict) or not athlete_data.get("id"):
                continue

            pid = str(athlete_data.get("id", ""))
            if player_id and pid != player_id:
                continue

            # Parse stats from core API response
            stat_map: dict[str, float] = {}
            if i < len(stats_results) and isinstance(stats_results[i], dict):
                stat_data = stats_results[i]
                for split in stat_data.get("splits", {}).get("categories", []):
                    for s in split.get("stats", []):
                        try:
                            stat_map[s["name"]] = float(s.get("value", 0))
                        except (ValueError, TypeError, KeyError):
                            pass

            # Resolve team name once
            if not team_name:
                team_ref = athlete_data.get("team", {})
                if isinstance(team_ref, dict) and "displayName" in team_ref:
                    team_name = team_ref["displayName"]

            gp = stat_map.get("gamesPlayed", 0)
            players.append(
                PlayerStats(
                    player_id=pid,
                    name=athlete_data.get("displayName", ""),
                    team=team_name,
                    position=_safe_get(athlete_data, "position", "abbreviation"),
                    games_played=int(gp),
                    minutes_per_game=stat_map.get("avgMinutes", 0),
                    ppg=stat_map.get("avgPoints", 0),
                    rpg=stat_map.get("avgRebounds", 0),
                    apg=stat_map.get("avgAssists", 0),
                    spg=stat_map.get("avgSteals", 0),
                    bpg=stat_map.get("avgBlocks", 0),
                    topg=stat_map.get("avgTurnovers", 0),
                    fg_pct=stat_map.get("fieldGoalPct", 0),
                    three_pct=stat_map.get("threePointFieldGoalPct", 0),
                    ft_pct=stat_map.get("freeThrowPct", 0),
                )
            )

        # Sort by PPG descending for readability
        players.sort(key=lambda p: p.ppg, reverse=True)
        return players

    async def get_stat_leaders(
        self, category: str = "scoring", season: int = 0
    ) -> list[StatLeader]:
        season = season or CURRENT_SEASON
        cat_map = {
            "scoring": "pointsPerGame",
            "rebounds": "reboundsPerGame",
            "assists": "assistsPerGame",
            "steals": "stealsPerGame",
            "blocks": "blocksPerGame",
            "field_goal_pct": "fieldGoalPct",
            "three_point_pct": "threePointFieldGoalPct",
            "free_throw_pct": "freeThrowPct",
        }
        stat_name = cat_map.get(category.lower(), "pointsPerGame")

        # Core API has the leaders data (site API 404s)
        try:
            data = await fetch_json(
                f"{ESPN_CORE_BASE}/seasons/{season}/types/2/leaders",
                params={"limit": "20"},
            )
        except Exception as e:
            raise SourceError(self.name, f"Failed to fetch leaders: {e}") from e

        # Find the matching category
        target_entries: list[dict] = []
        for cat_data in data.get("categories", []):
            if cat_data.get("name") == stat_name:
                target_entries = cat_data.get("leaders", [])
                break

        if not target_entries:
            return []

        # Resolve $ref links for athlete and team concurrently
        import asyncio
        athlete_refs = []
        team_refs = []
        for entry in target_entries[:20]:
            athlete_refs.append(entry.get("athlete", {}).get("$ref", ""))
            team_refs.append(entry.get("team", {}).get("$ref", ""))

        all_refs = athlete_refs + team_refs
        resolved: list = []
        try:
            tasks = [fetch_json(ref) for ref in all_refs if ref]
            resolved = await asyncio.gather(*tasks, return_exceptions=True)
        except Exception:
            pass

        # Split resolved results back into athletes and teams
        n = len(athlete_refs)
        athlete_data_list = resolved[:n] if len(resolved) >= n else resolved
        team_data_list = resolved[n:] if len(resolved) > n else []

        leaders: list[StatLeader] = []
        for i, entry in enumerate(target_entries[:20]):
            athlete_info = athlete_data_list[i] if i < len(athlete_data_list) and isinstance(athlete_data_list[i], dict) else {}
            team_info = team_data_list[i] if i < len(team_data_list) and isinstance(team_data_list[i], dict) else {}

            leaders.append(
                StatLeader(
                    rank=i + 1,
                    player_id=str(athlete_info.get("id", "")),
                    name=athlete_info.get("displayName", "Unknown"),
                    team=team_info.get("displayName", team_info.get("name", "")),
                    value=float(entry.get("value", 0)),
                    stat_category=category,
                )
            )
        return leaders

    # ── Private Parsers ─────────────────────────────────────────

    def _parse_event(self, event: dict) -> Game:
        """Parse an ESPN event into a Game model."""
        comp = event.get("competitions", [{}])[0] if event.get("competitions") else {}
        status_data = comp.get("status", event.get("status", {}))
        status_type = status_data.get("type", {})

        competitors = comp.get("competitors", [])
        home_data = {}
        away_data = {}
        for c in competitors:
            if c.get("homeAway") == "home":
                home_data = c
            else:
                away_data = c

        broadcasts = comp.get("broadcasts", [])
        broadcast_name = ""
        if broadcasts:
            names = broadcasts[0].get("names", [])
            broadcast_name = names[0] if names else ""

        notes = ""
        if comp.get("notes"):
            notes = comp["notes"][0].get("headline", "")

        return Game(
            id=str(event.get("id", "")),
            date=event.get("date", ""),
            status=status_type.get("state", ""),
            status_detail=status_type.get("detail", status_type.get("shortDetail", "")),
            period=status_data.get("period", 0),
            clock=status_data.get("displayClock", ""),
            venue=_safe_get(comp, "venue", "fullName"),
            broadcast=broadcast_name,
            conference_game=comp.get("conferenceCompetition", False),
            neutral_site=comp.get("neutralSite", False),
            home=self._parse_competitor(home_data),
            away=self._parse_competitor(away_data),
            notes=notes,
        )

    def _parse_competitor(self, data: dict) -> TeamScore:
        """Parse a competitor from an ESPN event."""
        team_data = data.get("team", {})
        records = data.get("records", [])
        record_str = records[0].get("summary", "") if records else ""

        rank = 0
        cur_rank = data.get("curatedRank", {})
        if cur_rank and cur_rank.get("current", 99) <= 25:
            rank = cur_rank["current"]

        line_scores = []
        for ls in data.get("linescores", []):
            try:
                line_scores.append(int(ls.get("value", 0)))
            except (ValueError, TypeError):
                pass

        # ESPN sometimes returns score as a dict for future games
        raw_score = data.get("score", 0)
        if isinstance(raw_score, dict):
            raw_score = raw_score.get("value", 0)
        try:
            score = int(raw_score)
        except (ValueError, TypeError):
            score = 0

        return TeamScore(
            team_id=str(team_data.get("id", "")),
            team_name=team_data.get("displayName", team_data.get("name", "")),
            abbreviation=team_data.get("abbreviation", ""),
            score=score,
            rank=rank if rank > 0 else None,
            record=record_str,
            logo_url=team_data.get("logo", ""),
            line_scores=line_scores,
        )

    def _parse_team(self, data: dict) -> Team:
        """Parse team data into a Team model."""
        record = Record()
        for rec in data.get("record", {}).get("items", []):
            summary = rec.get("summary", "0-0")
            rec_type = rec.get("type", "")
            parts = summary.split("-")
            if len(parts) == 2:
                try:
                    w, l = int(parts[0]), int(parts[1])
                    if rec_type == "total":
                        record.wins = w
                        record.losses = l
                    elif rec_type == "vsconf":
                        record.conference_wins = w
                        record.conference_losses = l
                except ValueError:
                    pass

        rank = None
        if data.get("rank"):
            try:
                r = int(data["rank"])
                if 1 <= r <= 25:
                    rank = r
            except (ValueError, TypeError):
                pass

        venue = Venue()
        venue_data = data.get("venue", data.get("franchiseVenue", {}))
        if venue_data:
            venue = Venue(
                name=venue_data.get("fullName", ""),
                city=venue_data.get("address", {}).get("city", ""),
                state=venue_data.get("address", {}).get("state", ""),
                capacity=venue_data.get("capacity", 0),
            )

        groups = data.get("groups", {})
        conference = ""
        if groups:
            if isinstance(groups, dict):
                conference = groups.get("name", "")
            elif isinstance(groups, list) and groups:
                conference = groups[0].get("name", "")

        logo_url = ""
        logos = data.get("logos", [])
        if logos:
            logo_url = logos[0].get("href", "")

        return Team(
            id=str(data.get("id", "")),
            name=data.get("displayName", data.get("name", "")),
            abbreviation=data.get("abbreviation", ""),
            mascot=data.get("nickname", ""),
            conference=conference,
            logo_url=logo_url,
            color=data.get("color", ""),
            record=record,
            rank=rank,
            venue=venue,
        )

    def _parse_summary_header(self, header: dict, comp: dict) -> Game:
        """Parse game summary header into a Game."""
        competitors = comp.get("competitors", [])
        home_data = {}
        away_data = {}
        for c in competitors:
            if c.get("homeAway") == "home":
                home_data = c
            else:
                away_data = c

        status_data = header.get("competitions", [{}])[0].get("status", {})
        if not status_data:
            status_data = comp.get("status", {})
        status_type = status_data.get("type", {})

        def parse_score_competitor(c: dict) -> TeamScore:
            team = c.get("team", {})
            rank = None
            ranks = c.get("ranks", [])
            if ranks:
                r = ranks[0].get("current", 99)
                if 1 <= r <= 25:
                    rank = r

            line_scores = []
            for ls in c.get("linescores", []):
                try:
                    line_scores.append(int(ls.get("displayValue", 0)))
                except (ValueError, TypeError):
                    pass

            records = c.get("record", [])
            record_str = ""
            if records:
                for r in records:
                    if r.get("type") == "total":
                        record_str = r.get("displayValue", "")
                        break
                if not record_str:
                    record_str = records[0].get("displayValue", "")

            # ESPN sometimes returns score as a dict for future games
            raw_score = c.get("score", 0)
            if isinstance(raw_score, dict):
                raw_score = raw_score.get("value", 0)
            try:
                score_val = int(raw_score)
            except (ValueError, TypeError):
                score_val = 0

            return TeamScore(
                team_id=str(team.get("id", "")),
                team_name=team.get("displayName", team.get("name", "")),
                abbreviation=team.get("abbreviation", ""),
                score=score_val,
                rank=rank,
                record=record_str,
                logo_url=team.get("logo", ""),
                line_scores=line_scores,
            )

        broadcasts = comp.get("broadcasts", [])
        broadcast_name = ""
        if broadcasts:
            names = broadcasts[0].get("names", [])
            broadcast_name = names[0] if names else ""

        return Game(
            id=str(header.get("id", "")),
            date=comp.get("date", ""),
            status=status_type.get("state", ""),
            status_detail=status_type.get("detail", ""),
            period=status_data.get("period", 0),
            clock=status_data.get("displayClock", ""),
            venue=_safe_get(comp, "venue", "fullName"),
            broadcast=broadcast_name,
            conference_game=comp.get("conferenceCompetition", False),
            neutral_site=comp.get("neutralSite", False),
            home=parse_score_competitor(home_data),
            away=parse_score_competitor(away_data),
        )

    def _parse_team_box(self, data: dict) -> TeamBoxScore:
        """Parse team box score data."""
        team = data.get("team", {})
        players: list[PlayerBoxScore] = []

        for stat_group in data.get("statistics", []):
            labels = [l.lower() for l in stat_group.get("labels", [])]
            for athlete in stat_group.get("athletes", []):
                athlete_info = athlete.get("athlete", {})
                stats = athlete.get("stats", [])
                stat_dict: dict[str, str] = {}
                for j, label in enumerate(labels):
                    if j < len(stats):
                        stat_dict[label] = stats[j]

                def safe_int(val: str) -> int:
                    try:
                        return int(val)
                    except (ValueError, TypeError):
                        return 0

                def safe_float(val: str) -> float:
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return 0.0

                def parse_made_att(val: str) -> tuple[int, int]:
                    if "-" in val:
                        parts = val.split("-")
                        return safe_int(parts[0]), safe_int(parts[1])
                    return 0, 0

                fg = parse_made_att(stat_dict.get("fg", "0-0"))
                tp = parse_made_att(stat_dict.get("3pt", "0-0"))
                ft = parse_made_att(stat_dict.get("ft", "0-0"))

                players.append(
                    PlayerBoxScore(
                        player_id=str(athlete_info.get("id", "")),
                        name=athlete_info.get("displayName", ""),
                        position=athlete_info.get("position", {}).get(
                            "abbreviation", ""
                        ),
                        minutes=stat_dict.get("min", "0"),
                        points=safe_int(stat_dict.get("pts", "0")),
                        rebounds=safe_int(stat_dict.get("reb", "0")),
                        assists=safe_int(stat_dict.get("ast", "0")),
                        steals=safe_int(stat_dict.get("stl", "0")),
                        blocks=safe_int(stat_dict.get("blk", "0")),
                        turnovers=safe_int(stat_dict.get("to", "0")),
                        fouls=safe_int(stat_dict.get("pf", "0")),
                        fgm=fg[0],
                        fga=fg[1],
                        fg_pct=safe_float(stat_dict.get("fg%", "0")),
                        tpm=tp[0],
                        tpa=tp[1],
                        tp_pct=safe_float(stat_dict.get("3pt%", "0")),
                        ftm=ft[0],
                        fta=ft[1],
                        ft_pct=safe_float(stat_dict.get("ft%", "0")),
                        offensive_rebounds=safe_int(stat_dict.get("oreb", "0")),
                        defensive_rebounds=safe_int(stat_dict.get("dreb", "0")),
                    )
                )

        # Calculate totals
        totals = PlayerBoxScore(name="TOTALS")
        for p in players:
            totals.points += p.points
            totals.rebounds += p.rebounds
            totals.assists += p.assists
            totals.steals += p.steals
            totals.blocks += p.blocks
            totals.turnovers += p.turnovers
            totals.fouls += p.fouls
            totals.fgm += p.fgm
            totals.fga += p.fga
            totals.tpm += p.tpm
            totals.tpa += p.tpa
            totals.ftm += p.ftm
            totals.fta += p.fta

        if totals.fga:
            totals.fg_pct = round(totals.fgm / totals.fga * 100, 1)
        if totals.tpa:
            totals.tp_pct = round(totals.tpm / totals.tpa * 100, 1)
        if totals.fta:
            totals.ft_pct = round(totals.ftm / totals.fta * 100, 1)

        return TeamBoxScore(
            team_id=str(team.get("id", "")),
            team_name=team.get("displayName", ""),
            players=players,
            totals=totals,
        )
