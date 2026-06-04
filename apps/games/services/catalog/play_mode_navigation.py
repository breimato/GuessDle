from apps.games.models import Game, GameMode
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.services.catalog.mode_select_service import ModeSelectService


def next_mode_navigation(game: Game, user, mode: GameMode | None) -> dict:
    empty = {"next_mode_url": "", "next_mode_label": ""}
    if not mode or not ModeResolver(game).has_modes():
        return empty

    entry = ModeSelectService(game, user).next_playable_entry(mode)
    if not entry:
        return empty

    return {
        "next_mode_url": entry["play_url"],
        "next_mode_label": entry["mode"].label,
    }
