LEAGUE_GAME_SLUG = "league-of-legends"
LEAGUE_GAME_SLUG_ALIASES = (LEAGUE_GAME_SLUG, "lol")


def is_league_game(slug: str) -> bool:
    return slug in LEAGUE_GAME_SLUG_ALIASES
