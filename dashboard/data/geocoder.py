"""
Venue coordinate resolution: static lookup + optional geopy fallback.
"""

from __future__ import annotations

from dashboard.data.venue_coordinates import STATE_CENTROIDS, VENUE_COORDS

# Runtime cache for dynamically resolved team → coords
_runtime_cache: dict[str, tuple[float, float]] = {}


def get_coords(
    team_name: str = "",
    city: str = "",
    state: str = "",
) -> tuple[float, float] | None:
    """
    Resolve (lat, lon) for a team/venue.
    Priority: exact team name → city+state geopy → state centroid.
    """
    # 1. Exact team name lookup
    if team_name and team_name in VENUE_COORDS:
        return VENUE_COORDS[team_name]

    # 2. Runtime cache (dynamically populated)
    cache_key = team_name or f"{city},{state}"
    if cache_key in _runtime_cache:
        return _runtime_cache[cache_key]

    # 3. Try partial team name match
    if team_name:
        team_lower = team_name.lower()
        for key, coords in VENUE_COORDS.items():
            if key.lower() in team_lower or team_lower in key.lower():
                _runtime_cache[team_name] = coords
                return coords

    # 4. Try geopy if city+state available (best-effort, non-blocking)
    if city and state:
        coords = _try_geopy(city, state)
        if coords:
            _runtime_cache[cache_key] = coords
            return coords

    # 5. State centroid fallback
    if state and state.upper() in STATE_CENTROIDS:
        return STATE_CENTROIDS[state.upper()]

    return None


def _try_geopy(city: str, state: str) -> tuple[float, float] | None:
    """Best-effort geocode via geopy Nominatim (not used in hot path)."""
    try:
        from geopy.geocoders import Nominatim
        from geopy.exc import GeocoderTimedOut

        geolocator = Nominatim(user_agent="cbb-dashboard/1.0")
        location = geolocator.geocode(f"{city}, {state}, USA", timeout=5)
        if location:
            return (location.latitude, location.longitude)
    except Exception:
        pass
    return None


def cache_coords(team_name: str, lat: float, lon: float) -> None:
    """Manually cache resolved coordinates for a team."""
    _runtime_cache[team_name] = (lat, lon)
