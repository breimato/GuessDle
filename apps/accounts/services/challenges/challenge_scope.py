from apps.accounts.services.dashboard.ranking_scope import (
    RANKING_PLAY_TYPES,
    is_ranking_mode,
    ranking_modes_for_game,
)
from apps.games.models import Game, GameMode
from apps.games.services.catalog.mode_resolver import ModeResolver

CHALLENGE_PLAY_TYPES = RANKING_PLAY_TYPES

is_challengeable_mode = is_ranking_mode
challenge_modes_for_game = ranking_modes_for_game


def is_challengeable_game(game: Game) -> bool:
    resolver = ModeResolver(game)
    if not resolver.has_modes():
        return True
    return bool(challenge_modes_for_game(game))


def requires_challenge_mode_selection(game: Game) -> bool:
    return len(challenge_modes_for_game(game)) > 1


def resolve_challenge_mode(
    game: Game, mode_slug: str | None
) -> tuple[GameMode | None, str | None]:
    resolver = ModeResolver(game)
    modes = challenge_modes_for_game(game)

    if not resolver.has_modes():
        return None, None

    if mode_slug:
        mode = resolver.resolve(mode_slug)
        if not is_challengeable_mode(mode):
            return None, "Solo puedes retar en modos Wordle."
        return mode, None

    if len(modes) == 1:
        return modes[0], None

    if requires_challenge_mode_selection(game):
        return None, "Debes elegir una dificultad."

    return None, "Solo puedes retar en modos Wordle."


def assert_challengeable_game_and_mode(game: Game, mode: GameMode | None) -> str | None:
    if not is_challengeable_game(game):
        return "Solo puedes retar en modos Wordle."
    if mode is not None and not is_challengeable_mode(mode):
        return "Solo puedes retar en modos Wordle."
    return None
