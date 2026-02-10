"""Response formatting helpers for MCP tool output."""

from cbb_mcp.models.games import BoxScore, Game, PlayByPlay
from cbb_mcp.models.rankings import ConferenceStandings, Poll
from cbb_mcp.models.stats import PlayerStats, StatLeader, TeamComparison, TeamStats
from cbb_mcp.models.teams import Player, Team


def format_game(game: Game) -> str:
    """Format a single game for display."""
    away = game.away.display_name
    home = game.home.display_name

    if game.status == "pre":
        time_str = game.date
        return f"{away} at {home} — {game.status_detail}\n  TV: {game.broadcast}" if game.broadcast else f"{away} at {home} — {game.status_detail}"

    score_line = f"{away} {game.away.score} - {home} {game.home.score}"
    status = game.status_detail or ("Final" if game.status == "post" else "In Progress")
    return f"{score_line}  ({status})"


def format_scores(games: list[Game]) -> str:
    """Format a list of games/scores."""
    if not games:
        return "No games found for this date."
    lines = [format_game(g) for g in games]
    return "\n".join(lines)


def format_team(team: Team) -> str:
    """Format team info."""
    parts = [f"**{team.display_name}**"]
    if team.conference:
        parts.append(f"Conference: {team.conference}")
    if team.record.wins or team.record.losses:
        parts.append(f"Record: {team.record.overall}")
        if team.record.conference_wins or team.record.conference_losses:
            parts.append(f"Conference: {team.record.conference}")
    if team.venue.name:
        parts.append(f"Arena: {team.venue.name}")
    return "\n".join(parts)


def format_roster(team: Team, players: list[Player]) -> str:
    """Format team roster."""
    lines = [f"**{team.display_name} Roster**\n"]
    for p in players:
        line = f"#{p.jersey} {p.name}"
        details = []
        if p.position:
            details.append(p.position)
        if p.height:
            details.append(p.height)
        if p.year:
            details.append(p.year)
        if details:
            line += f" ({', '.join(details)})"
        lines.append(line)
    return "\n".join(lines) if players else f"No roster data available for {team.name}."


def format_schedule(team: Team, games: list[Game]) -> str:
    """Format team schedule."""
    lines = [f"**{team.display_name} Schedule**\n"]
    for g in games:
        is_home = g.home.team_id == team.id
        opponent = g.away if is_home else g.home
        prefix = "vs" if is_home else "@"
        opp_name = opponent.display_name

        if g.status == "post":
            team_score = g.home.score if is_home else g.away.score
            opp_score = opponent.score
            result = "W" if team_score > opp_score else "L"
            lines.append(f"{g.date[:10]}  {result} {prefix} {opp_name}  {team_score}-{opp_score}")
        elif g.status == "in":
            team_score = g.home.score if is_home else g.away.score
            lines.append(f"{g.date[:10]}  LIVE {prefix} {opp_name}  {team_score}-{opponent.score} ({g.status_detail})")
        else:
            lines.append(f"{g.date[:10]}  {prefix} {opp_name}  {g.status_detail}")

    return "\n".join(lines) if len(lines) > 1 else f"No schedule data available for {team.name}."


def format_box_score(box: BoxScore) -> str:
    """Format a box score."""
    lines = [format_game(box.game), ""]

    for label, team_box in [("Away", box.away), ("Home", box.home)]:
        lines.append(f"**{team_box.team_name or label}**")
        lines.append(f"{'Player':<22} {'MIN':>4} {'PTS':>4} {'REB':>4} {'AST':>4} {'STL':>4} {'BLK':>4} {'FG':>7}")
        lines.append("-" * 65)
        for p in team_box.players:
            fg = f"{p.fgm}-{p.fga}" if p.fga else "-"
            lines.append(
                f"{p.name:<22} {p.minutes:>4} {p.points:>4} {p.rebounds:>4} "
                f"{p.assists:>4} {p.steals:>4} {p.blocks:>4} {fg:>7}"
            )
        t = team_box.totals
        lines.append("-" * 65)
        lines.append(
            f"{'TOTALS':<22} {'':>4} {t.points:>4} {t.rebounds:>4} "
            f"{t.assists:>4} {t.steals:>4} {t.blocks:>4} {t.fgm}-{t.fga}:>7"
        )
        lines.append("")

    return "\n".join(lines)


def format_play_by_play(pbp: PlayByPlay, last_n: int = 20) -> str:
    """Format play-by-play data."""
    lines = [format_game(pbp.game), ""]
    plays = pbp.plays[-last_n:] if last_n else pbp.plays

    for p in plays:
        score = f"[{p.score_away}-{p.score_home}]"
        marker = "*" if p.scoring_play else " "
        lines.append(f"P{p.period} {p.clock:>6}  {score:>9} {marker} {p.description}")

    if last_n and len(pbp.plays) > last_n:
        lines.insert(2, f"(Showing last {last_n} of {len(pbp.plays)} plays)\n")

    return "\n".join(lines)


def format_rankings(poll: Poll) -> str:
    """Format poll rankings."""
    lines = [f"**{poll.name}** (Week {poll.week})\n"]
    for t in poll.teams:
        trend_str = ""
        if t.trend == "up":
            trend_str = f" (+{t.previous_rank - t.rank})"
        elif t.trend == "down":
            trend_str = f" (-{t.rank - t.previous_rank})"
        elif t.trend == "new":
            trend_str = " (NEW)"

        lines.append(f"{t.rank:>3}. {t.team_name:<26} {t.record:<8} {t.points:>5} pts{trend_str}")

    return "\n".join(lines)


def format_standings(standings_list: list[ConferenceStandings]) -> str:
    """Format conference standings."""
    lines: list[str] = []
    for standings in standings_list:
        lines.append(f"**{standings.conference}**")
        lines.append(f"{'#':>3}  {'Team':<28} {'Overall':<10} {'Conf':<10} {'Streak':<8}")
        lines.append("-" * 65)
        for t in standings.teams:
            lines.append(
                f"{t.conference_rank:>3}  {t.team_name:<28} {t.overall_record:<10} "
                f"{t.conference_record:<10} {t.streak:<8}"
            )
        lines.append("")
    return "\n".join(lines) if lines else "No standings data available."


def format_team_stats(stats: TeamStats) -> str:
    """Format team statistics."""
    return (
        f"**{stats.team_name}** Season Stats\n"
        f"PPG: {stats.ppg:.1f} | Opp PPG: {stats.opp_ppg:.1f}\n"
        f"FG%: {stats.fg_pct:.1f} | 3PT%: {stats.three_pct:.1f} | FT%: {stats.ft_pct:.1f}\n"
        f"RPG: {stats.rpg:.1f} | APG: {stats.apg:.1f}\n"
        f"SPG: {stats.spg:.1f} | BPG: {stats.bpg:.1f} | TOPG: {stats.topg:.1f}"
    )


def format_player_stats(players: list[PlayerStats]) -> str:
    """Format player statistics table."""
    if not players:
        return "No player stats available."

    lines = [f"{'Player':<24} {'Pos':>4} {'GP':>3} {'PPG':>5} {'RPG':>5} {'APG':>5} {'FG%':>5} {'3P%':>5}"]
    lines.append("-" * 65)
    for p in players:
        lines.append(
            f"{p.name:<24} {p.position:>4} {p.games_played:>3} {p.ppg:>5.1f} "
            f"{p.rpg:>5.1f} {p.apg:>5.1f} {p.fg_pct:>5.1f} {p.three_pct:>5.1f}"
        )
    return "\n".join(lines)


def format_stat_leaders(leaders: list[StatLeader]) -> str:
    """Format stat leaders."""
    if not leaders:
        return "No stat leader data available."

    category = leaders[0].stat_category if leaders else ""
    lines = [f"**National {category.title()} Leaders**\n"]
    for l in leaders:
        lines.append(f"{l.rank:>3}. {l.name:<24} {l.team:<20} {l.value:.1f}")
    return "\n".join(lines)


def format_comparison(comp: TeamComparison) -> str:
    """Format team comparison."""
    lines = [f"**{comp.team1.team_name} vs {comp.team2.team_name}**\n"]
    lines.append(f"{'Stat':<24} {comp.team1.team_name:>14} {comp.team2.team_name:>14} {'Advantage':>14}")
    lines.append("-" * 70)

    stat_rows = [
        ("PPG", f"{comp.team1.ppg:.1f}", f"{comp.team2.ppg:.1f}"),
        ("Opp PPG", f"{comp.team1.opp_ppg:.1f}", f"{comp.team2.opp_ppg:.1f}"),
        ("FG%", f"{comp.team1.fg_pct:.1f}", f"{comp.team2.fg_pct:.1f}"),
        ("3PT%", f"{comp.team1.three_pct:.1f}", f"{comp.team2.three_pct:.1f}"),
        ("FT%", f"{comp.team1.ft_pct:.1f}", f"{comp.team2.ft_pct:.1f}"),
        ("RPG", f"{comp.team1.rpg:.1f}", f"{comp.team2.rpg:.1f}"),
        ("APG", f"{comp.team1.apg:.1f}", f"{comp.team2.apg:.1f}"),
        ("SPG", f"{comp.team1.spg:.1f}", f"{comp.team2.spg:.1f}"),
        ("BPG", f"{comp.team1.bpg:.1f}", f"{comp.team2.bpg:.1f}"),
        ("TOPG", f"{comp.team1.topg:.1f}", f"{comp.team2.topg:.1f}"),
    ]

    labels_map = {
        "PPG": "Points Per Game",
        "Opp PPG": "Opp Points Per Game",
        "FG%": "FG%",
        "3PT%": "3PT%",
        "FT%": "FT%",
        "RPG": "Rebounds Per Game",
        "APG": "Assists Per Game",
        "SPG": "Steals Per Game",
        "BPG": "Blocks Per Game",
        "TOPG": "Turnovers Per Game",
    }

    for label, v1, v2 in stat_rows:
        adv_key = labels_map.get(label, label)
        adv = comp.advantages.get(adv_key, "")
        lines.append(f"{label:<24} {v1:>14} {v2:>14} {adv:>14}")

    return "\n".join(lines)
