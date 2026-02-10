"""Game/score service layer with caching."""

from cbb_mcp.models.games import BoxScore, Game, PlayByPlay
from cbb_mcp.services.resolver import resolve
from cbb_mcp.sources.base import DataCapability
from cbb_mcp.utils import cache
from cbb_mcp.utils.constants import CACHE_TTL


async def get_live_scores(
    date: str, conference: str = "", top25: bool = False
) -> list[Game]:
    cache_key_args = [date, conference, str(top25)]
    cached = cache.get("live_scores", *cache_key_args)
    if cached:
        return [Game(**g) if isinstance(g, dict) else g for g in cached]

    games = await resolve(
        DataCapability.LIVE_SCORES,
        "get_live_scores",
        date=date,
        conference=conference,
        top25=top25,
    )
    cache.put(
        "live_scores",
        *cache_key_args,
        data=[g.model_dump() for g in games],
        ttl=CACHE_TTL["live_scores"],
    )
    return games


async def get_game_detail(game_id: str) -> Game:
    cached = cache.get("game_detail", game_id)
    if cached:
        return Game(**cached) if isinstance(cached, dict) else cached

    game = await resolve(
        DataCapability.GAME_DETAIL, "get_game_detail", game_id=game_id
    )
    cache.put(
        "game_detail", game_id, data=game.model_dump(), ttl=CACHE_TTL["game_detail"]
    )
    return game


async def get_box_score(game_id: str) -> BoxScore:
    cached = cache.get("box_score", game_id)
    if cached:
        return BoxScore(**cached) if isinstance(cached, dict) else cached

    box = await resolve(
        DataCapability.BOX_SCORE, "get_box_score", game_id=game_id
    )
    cache.put(
        "box_score", game_id, data=box.model_dump(), ttl=CACHE_TTL["box_score"]
    )
    return box


async def get_play_by_play(game_id: str) -> PlayByPlay:
    cached = cache.get("play_by_play", game_id)
    if cached:
        return PlayByPlay(**cached) if isinstance(cached, dict) else cached

    pbp = await resolve(
        DataCapability.PLAY_BY_PLAY, "get_play_by_play", game_id=game_id
    )
    cache.put(
        "play_by_play", game_id, data=pbp.model_dump(), ttl=CACHE_TTL["play_by_play"]
    )
    return pbp
