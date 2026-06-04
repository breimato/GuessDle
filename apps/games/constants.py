POKEMON_GAME_SLUG = "pokemon"
POKEMON_GAME_SLUG_ALIASES = (POKEMON_GAME_SLUG,)

LEAGUE_GAME_SLUG = "league-of-legends"
LEAGUE_GAME_SLUG_ALIASES = (LEAGUE_GAME_SLUG, "lol")

ONE_PIECE_GAME_SLUG = "one-piece"
ONE_PIECE_GAME_SLUG_ALIASES = (ONE_PIECE_GAME_SLUG,)

DEFAULT_WORDLE_MODE_SLUG = "normal"
DAILY_WORDLE_MODE_LABEL = "Diario"

POKEMON_WORDLE_MODE_LABELS = {
    "normal": "Normal",
    "dificil": "Difícil",
    "radical": "Radical",
}


def is_pokemon_game(slug: str) -> bool:
    return slug in POKEMON_GAME_SLUG_ALIASES or slug.startswith("pokemon")


def is_league_game(slug: str) -> bool:
    return slug in LEAGUE_GAME_SLUG_ALIASES


def is_one_piece_game(slug: str) -> bool:
    return slug in ONE_PIECE_GAME_SLUG_ALIASES or slug.startswith("one-piece")


def default_wordle_mode_label(game_slug: str, mode_slug: str = DEFAULT_WORDLE_MODE_SLUG) -> str:
    if is_pokemon_game(game_slug):
        return POKEMON_WORDLE_MODE_LABELS.get(mode_slug, mode_slug)
    if mode_slug == DEFAULT_WORDLE_MODE_SLUG:
        return DAILY_WORDLE_MODE_LABEL
    return mode_slug
