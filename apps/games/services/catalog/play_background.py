from apps.games.models import Game, GameMode


def resolve_background_url(game: Game, mode: GameMode | None = None) -> str | None:
    if mode and mode.background_image:
        return mode.background_image.url
    if game.background_image:
        return game.background_image.url
    return None
