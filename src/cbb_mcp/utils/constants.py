"""Static constants: conference IDs, ESPN team mappings, etc."""

# ESPN group IDs for conferences
ESPN_CONFERENCES: dict[str, dict] = {
    "ACC": {"id": "2", "name": "Atlantic Coast Conference"},
    "Big 12": {"id": "8", "name": "Big 12 Conference"},
    "Big East": {"id": "4", "name": "Big East Conference"},
    "Big Ten": {"id": "7", "name": "Big Ten Conference"},
    "SEC": {"id": "3", "name": "Southeastern Conference"},
    "Pac-12": {"id": "21", "name": "Pac-12 Conference"},
    "AAC": {"id": "62", "name": "American Athletic Conference"},
    "A-10": {"id": "6", "name": "Atlantic 10 Conference"},
    "Mountain West": {"id": "44", "name": "Mountain West Conference"},
    "WCC": {"id": "5", "name": "West Coast Conference"},
    "MVC": {"id": "9", "name": "Missouri Valley Conference"},
    "C-USA": {"id": "11", "name": "Conference USA"},
    "MAC": {"id": "12", "name": "Mid-American Conference"},
    "Sun Belt": {"id": "37", "name": "Sun Belt Conference"},
    "CAA": {"id": "10", "name": "Colonial Athletic Association"},
    "Ivy": {"id": "22", "name": "Ivy League"},
    "MAAC": {"id": "13", "name": "Metro Atlantic Athletic Conference"},
    "Horizon": {"id": "45", "name": "Horizon League"},
    "WAC": {"id": "23", "name": "Western Athletic Conference"},
    "Southern": {"id": "24", "name": "Southern Conference"},
    "Big South": {"id": "40", "name": "Big South Conference"},
    "OVC": {"id": "16", "name": "Ohio Valley Conference"},
    "Summit": {"id": "49", "name": "Summit League"},
    "Patriot": {"id": "15", "name": "Patriot League"},
    "NEC": {"id": "18", "name": "Northeast Conference"},
    "SWAC": {"id": "26", "name": "Southwestern Athletic Conference"},
    "MEAC": {"id": "17", "name": "Mid-Eastern Athletic Conference"},
    "Southland": {"id": "25", "name": "Southland Conference"},
    "Big Sky": {"id": "20", "name": "Big Sky Conference"},
    "Big West": {"id": "19", "name": "Big West Conference"},
    "America East": {"id": "14", "name": "America East Conference"},
    "ASUN": {"id": "27", "name": "Atlantic Sun Conference"},
}

# ESPN API base URLs
ESPN_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
ESPN_CORE_BASE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball"

# NCAA API base (henrygd)
NCAA_API_BASE = "https://ncaa-api.henrygd.me"

# Current season
CURRENT_SEASON = 2025  # 2024-25 season

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
