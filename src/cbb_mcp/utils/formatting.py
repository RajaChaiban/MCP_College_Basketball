"""Response formatting helpers for MCP tool output."""

from cbb_mcp.models.games import BoxScore, Game, PlayByPlay
from cbb_mcp.models.rankings import ConferenceStandings, Poll
from cbb_mcp.models.stats import PlayerStats, StatLeader, TeamComparison, TeamStats
from cbb_mcp.models.teams import Player, Team


def format_game(game: Game) -> str:
    """Format a single game for display."""
    away = game.away.display_name
    home = game.home.display_name
    game_id_tag = f"  [Game ID: {game.id}]" if game.id else ""

    if game.status == "pre":
        line = f"{away} at {home} — {game.status_detail}\n  TV: {game.broadcast}" if game.broadcast else f"{away} at {home} — {game.status_detail}"
        return line + game_id_tag

    score_line = f"{away} {game.away.score} - {home} {game.home.score}"
    status = game.status_detail or ("Final" if game.status == "post" else "In Progress")
    return f"{score_line}  ({status}){game_id_tag}"


def format_game_detail(game: Game) -> str:
    """Format comprehensive game details for get_game_detail tool."""
    lines = [format_game(game), ""]

    # Venue, broadcast, date
    if game.venue:
        lines.append(f"Venue: {game.venue}")
    if game.broadcast:
        lines.append(f"Broadcast: {game.broadcast}")
    if game.date:
        lines.append(f"Date: {game.date}")

    # Flags
    flags = []
    if game.conference_game:
        flags.append("Conference Game")
    if game.neutral_site:
        flags.append("Neutral Site")
    if flags:
        lines.append(" | ".join(flags))

    # Team records
    if game.away.record:
        lines.append(f"{game.away.display_name} Record: {game.away.record}")
    if game.home.record:
        lines.append(f"{game.home.display_name} Record: {game.home.record}")

    # Half-by-half scoring
    line_scores = _format_line_scores(game)
    if line_scores:
        lines.append("")
        lines.extend(line_scores)

    # Live game status
    if game.status == "in" and (game.period or game.clock):
        lines.append("")
        parts = []
        if game.period:
            parts.append(f"Period: {game.period}")
        if game.clock:
            parts.append(f"Clock: {game.clock}")
        lines.append(" | ".join(parts))

    return "\n".join(lines)


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

        id_tag = f"  [ID: {g.id}]" if g.id else ""
        if g.status == "post":
            team_score = g.home.score if is_home else g.away.score
            opp_score = opponent.score
            result = "W" if team_score > opp_score else "L"
            lines.append(f"{g.date[:10]}  {result} {prefix} {opp_name}  {team_score}-{opp_score}{id_tag}")
        elif g.status == "in":
            team_score = g.home.score if is_home else g.away.score
            lines.append(f"{g.date[:10]}  LIVE {prefix} {opp_name}  {team_score}-{opponent.score} ({g.status_detail}){id_tag}")
        else:
            lines.append(f"{g.date[:10]}  {prefix} {opp_name}  {g.status_detail}{id_tag}")

    return "\n".join(lines) if len(lines) > 1 else f"No schedule data available for {team.name}."


def _format_line_scores(game: Game) -> list[str]:
    """Render half-by-half scoring table using TeamScore.line_scores."""
    away_ls = game.away.line_scores
    home_ls = game.home.line_scores
    if not away_ls and not home_ls:
        return []

    num_periods = max(len(away_ls), len(home_ls))
    # Build period headers: 1st, 2nd, then OT, 2OT, etc.
    headers = []
    for i in range(num_periods):
        if i == 0:
            headers.append("1st")
        elif i == 1:
            headers.append("2nd")
        elif i == 2:
            headers.append("OT")
        else:
            headers.append(f"{i - 1}OT")

    header_line = f"{'Team':<22}" + "".join(f" {h:>5}" for h in headers) + f" {'Total':>6}"
    sep = "-" * len(header_line)

    def score_row(name: str, scores: list[int], total: int) -> str:
        row = f"{name:<22}"
        for i in range(num_periods):
            val = scores[i] if i < len(scores) else 0
            row += f" {val:>5}"
        row += f" {total:>6}"
        return row

    lines = [header_line, sep]
    lines.append(score_row(game.away.display_name, away_ls, game.away.score))
    lines.append(score_row(game.home.display_name, home_ls, game.home.score))
    return lines


def format_box_score(box: BoxScore) -> str:
    """Format a box score with full shooting splits."""
    lines = [format_game(box.game), ""]

    # Half-by-half scoring table
    line_scores = _format_line_scores(box.game)
    if line_scores:
        lines.extend(line_scores)
        lines.append("")

    header = (
        f"{'Player':<22} {'MIN':>4} {'PTS':>4} {'REB':>4} {'AST':>4} "
        f"{'STL':>4} {'BLK':>4} {'TO':>3} {'PF':>3} "
        f"{'FG':>7} {'FG%':>5} {'3PT':>7} {'3P%':>5} {'FT':>6} {'FT%':>5}"
    )
    sep = "-" * len(header)

    for label, team_box in [("Away", box.away), ("Home", box.home)]:
        lines.append(f"**{team_box.team_name or label}**")
        lines.append(header)
        lines.append(sep)
        for p in team_box.players:
            fg = f"{p.fgm}-{p.fga}" if p.fga else "-"
            tp = f"{p.tpm}-{p.tpa}" if p.tpa else "-"
            ft = f"{p.ftm}-{p.fta}" if p.fta else "-"
            fg_pct = f"{p.fg_pct:.0f}" if p.fga else "-"
            tp_pct = f"{p.tp_pct:.0f}" if p.tpa else "-"
            ft_pct = f"{p.ft_pct:.0f}" if p.fta else "-"
            lines.append(
                f"{p.name:<22} {p.minutes:>4} {p.points:>4} {p.rebounds:>4} "
                f"{p.assists:>4} {p.steals:>4} {p.blocks:>4} {p.turnovers:>3} {p.fouls:>3} "
                f"{fg:>7} {fg_pct:>5} {tp:>7} {tp_pct:>5} {ft:>6} {ft_pct:>5}"
            )
        t = team_box.totals
        lines.append(sep)
        t_fg = f"{t.fgm}-{t.fga}" if t.fga else "-"
        t_tp = f"{t.tpm}-{t.tpa}" if t.tpa else "-"
        t_ft = f"{t.ftm}-{t.fta}" if t.fta else "-"
        t_fg_pct = f"{t.fg_pct:.0f}" if t.fga else "-"
        t_tp_pct = f"{t.tp_pct:.0f}" if t.tpa else "-"
        t_ft_pct = f"{t.ft_pct:.0f}" if t.fta else "-"
        lines.append(
            f"{'TOTALS':<22} {'':>4} {t.points:>4} {t.rebounds:>4} "
            f"{t.assists:>4} {t.steals:>4} {t.blocks:>4} {t.turnovers:>3} {t.fouls:>3} "
            f"{t_fg:>7} {t_fg_pct:>5} {t_tp:>7} {t_tp_pct:>5} {t_ft:>6} {t_ft_pct:>5}"
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
    lines = [f"**{stats.team_name}** Season Stats"]
    if stats.games_played:
        lines.append(f"Games Played: {stats.games_played}")
    lines.append(f"PPG: {stats.ppg:.1f} | Opp PPG: {stats.opp_ppg:.1f}")
    lines.append(f"FG%: {stats.fg_pct:.1f} | 3PT%: {stats.three_pct:.1f} | FT%: {stats.ft_pct:.1f}")
    rpg_line = f"RPG: {stats.rpg:.1f}"
    if stats.offensive_rpg or stats.defensive_rpg:
        rpg_line += f" (Off: {stats.offensive_rpg:.1f} | Def: {stats.defensive_rpg:.1f})"
    rpg_line += f" | APG: {stats.apg:.1f}"
    lines.append(rpg_line)
    lines.append(f"SPG: {stats.spg:.1f} | BPG: {stats.bpg:.1f} | TOPG: {stats.topg:.1f}")
    return "\n".join(lines)


def format_player_stats(players: list[PlayerStats]) -> str:
    """Format player statistics table."""
    if not players:
        return "No player stats available."

    lines = [
        f"{'Player':<24} {'Pos':>4} {'GP':>3} {'MPG':>5} {'PPG':>5} {'RPG':>5} {'APG':>5} "
        f"{'SPG':>5} {'BPG':>5} {'TOPG':>5} {'FG%':>5} {'3P%':>5} {'FT%':>5}"
    ]
    lines.append("-" * 100)
    for p in players:
        lines.append(
            f"{p.name:<24} {p.position:>4} {p.games_played:>3} {p.minutes_per_game:>5.1f} {p.ppg:>5.1f} "
            f"{p.rpg:>5.1f} {p.apg:>5.1f} {p.spg:>5.1f} {p.bpg:>5.1f} {p.topg:>5.1f} "
            f"{p.fg_pct:>5.1f} {p.three_pct:>5.1f} {p.ft_pct:>5.1f}"
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
    ]

    # Add Off/Def RPG breakdown if data is available
    if comp.team1.offensive_rpg or comp.team2.offensive_rpg:
        stat_rows.append(("Off RPG", f"{comp.team1.offensive_rpg:.1f}", f"{comp.team2.offensive_rpg:.1f}"))
    if comp.team1.defensive_rpg or comp.team2.defensive_rpg:
        stat_rows.append(("Def RPG", f"{comp.team1.defensive_rpg:.1f}", f"{comp.team2.defensive_rpg:.1f}"))

    stat_rows.extend([
        ("APG", f"{comp.team1.apg:.1f}", f"{comp.team2.apg:.1f}"),
        ("SPG", f"{comp.team1.spg:.1f}", f"{comp.team2.spg:.1f}"),
        ("BPG", f"{comp.team1.bpg:.1f}", f"{comp.team2.bpg:.1f}"),
        ("TOPG", f"{comp.team1.topg:.1f}", f"{comp.team2.topg:.1f}"),
    ])

    labels_map = {
        "PPG": "Points Per Game",
        "Opp PPG": "Opp Points Per Game",
        "FG%": "FG%",
        "3PT%": "3PT%",
        "FT%": "FT%",
        "RPG": "Rebounds Per Game",
        "Off RPG": "Offensive Rebounds Per Game",
        "Def RPG": "Defensive Rebounds Per Game",
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
