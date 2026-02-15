"""Static constants: conference IDs, ESPN team mappings, etc."""

# ESPN web API group IDs for conferences
# (verified against site.web.api.espn.com standings endpoint)
ESPN_CONFERENCES: dict[str, dict] = {
    "ACC": {"id": "2", "name": "Atlantic Coast Conference"},
    "Big 12": {"id": "8", "name": "Big 12 Conference"},
    "Big East": {"id": "4", "name": "Big East Conference"},
    "Big Ten": {"id": "7", "name": "Big Ten Conference"},
    "SEC": {"id": "23", "name": "Southeastern Conference"},
    "AAC": {"id": "62", "name": "American Conference"},
    "A-10": {"id": "3", "name": "Atlantic 10 Conference"},
    "Mountain West": {"id": "44", "name": "Mountain West Conference"},
    "WCC": {"id": "29", "name": "West Coast Conference"},
    "MVC": {"id": "18", "name": "Missouri Valley Conference"},
    "C-USA": {"id": "11", "name": "Conference USA"},
    "MAC": {"id": "14", "name": "Mid-American Conference"},
    "Sun Belt": {"id": "27", "name": "Sun Belt Conference"},
    "CAA": {"id": "10", "name": "Coastal Athletic Association"},
    "Ivy": {"id": "12", "name": "Ivy League"},
    "MAAC": {"id": "13", "name": "Metro Atlantic Athletic Conference"},
    "Horizon": {"id": "45", "name": "Horizon League"},
    "WAC": {"id": "30", "name": "Western Athletic Conference"},
    "Southern": {"id": "24", "name": "Southern Conference"},
    "Big South": {"id": "6", "name": "Big South Conference"},
    "OVC": {"id": "20", "name": "Ohio Valley Conference"},
    "Summit": {"id": "49", "name": "Summit League"},
    "Patriot": {"id": "22", "name": "Patriot League"},
    "NEC": {"id": "19", "name": "Northeast Conference"},
    "SWAC": {"id": "26", "name": "Southwestern Athletic Conference"},
    "MEAC": {"id": "16", "name": "Mid-Eastern Athletic Conference"},
    "Southland": {"id": "25", "name": "Southland Conference"},
    "Big Sky": {"id": "5", "name": "Big Sky Conference"},
    "Big West": {"id": "9", "name": "Big West Conference"},
    "America East": {"id": "1", "name": "America East Conference"},
    "ASUN": {"id": "46", "name": "ASUN Conference"},
}

# ESPN API base URLs
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
ESPN_WEB_BASE = "https://site.web.api.espn.com/apis/v2/sports/basketball/mens-college-basketball"
ESPN_CORE_BASE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball"

# NCAA API base (henrygd)
NCAA_API_BASE = "https://ncaa-api.henrygd.me"

# Current season — auto-calculated from today's date.
# NCAA season spans two calendar years (e.g., 2025-26).
# ESPN uses the *ending* year as the season identifier.
# Games from November onward belong to the next season.
def _current_season() -> int:
    from datetime import date
    today = date.today()
    # If we're in Nov or later, we're in the season that ends next year
    if today.month >= 11:
        return today.year + 1
    # Jan–Oct: we're in the season that ends this year
    return today.year


CURRENT_SEASON = _current_season()

# Cache TTLs in seconds
CACHE_TTL = {
    "live_scores": 30,
    "game_detail": 60,
    "box_score": 60,
    "play_by_play": 120,
    "rankings": 3600,       # 1 hour
    "standings": 3600,
    "team_info": 86400,     # 24 hours
    "team_schedule": 3600,
    "roster": 86400,
    "team_stats": 3600,
    "player_stats": 3600,
    "stat_leaders": 3600,
    "conferences": 86400,
    "tournament": 300,      # 5 min during March
}
