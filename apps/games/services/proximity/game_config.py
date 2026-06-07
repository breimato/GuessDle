POKEMON_SLUG = "pokemon"
LEAGUE_SLUGS = ("league-of-legends", "lol")
ONE_PIECE_SLUG = "one-piece"
ONE_PIECE_MEDIA_MANGA = "manga"
ONE_PIECE_MEDIA_ANIME = "anime"

EVENT_POOL_WEIGHT = 0.4
LOL_RECENT_YEAR = 2013
LOL_RECENT_WEIGHT = 3
LOL_LEGACY_WEIGHT = 1

TEAM_TIMER_SECONDS = 60
PROXIMITY_TEAM_TIMER_NOTE = "Las cuentas de equipo tienen 1 minuto para responder."

POKEMON_REGIONS = {
    1: "Kanto",
    2: "Johto",
    3: "Hoenn",
    4: "Sinnoh",
    5: "Unova",
    6: "Kalos",
    7: "Alola",
    8: "Galar",
    9: "Paldea",
}


def lol_release_year(data: dict | None) -> int | None:
    if not data:
        return None
    raw = data.get("releaseDate")
    if raw is None:
        raw = data.get("Año") or data.get("Ano")
    try:
        return int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None


def proximity_game_kind(game) -> str | None:
    slug = game.slug
    if slug == POKEMON_SLUG or slug.startswith("pokemon"):
        return "pokemon"
    if slug in LEAGUE_SLUGS or slug.startswith("lol"):
        return "lol"
    if slug == ONE_PIECE_SLUG or slug.startswith("one-piece"):
        return "one_piece"
    attrs = set(game.attributes or [])
    if "releaseDate" in attrs or "Año" in attrs or "Ano" in attrs:
        return "lol"
    if "generacion" in attrs:
        return "pokemon"
    if "capítulo" in attrs or "capitulo" in attrs:
        return "one_piece"
    return None


def proximity_info_text(game) -> str:
    kind = proximity_game_kind(game)
    if kind == "pokemon":
        base = (
            "Hay que acertar el número de Pokédex que tiene el Pokémon indicado en un solo intento. "
            "Cuanto más cerca te quedes, mejor."
        )
    elif kind == "lol":
        base = (
            "Hay que acertar el año de lanzamiento que tiene el campeón indicado en un solo intento. "
            "Cuanto más cerca te quedes, mejor."
        )
    elif kind == "one_piece":
        base = (
            "Hay que acertar el capítulo del manga o el episodio del anime (según elijas en filtros) "
            "de la primera aparición del personaje o del evento indicado, en un solo intento. "
            "Cuanto más cerca te quedes, mejor."
        )
    else:
        base = (
            "Hay que acertar el número de lo que se pregunta en un solo intento. "
            "Cuanto más cerca te quedes, mejor."
        )
    return f"{base} {PROXIMITY_TEAM_TIMER_NOTE}"


def default_filters_for_game(game) -> dict:
    kind = proximity_game_kind(game)
    if kind == "pokemon":
        return {"generations": [1, 2, 3]}
    if kind == "lol":
        return {"years": []}
    if kind == "one_piece":
        return {"arcs": [], "media": ONE_PIECE_MEDIA_MANGA}
    return {}


def one_piece_value_unit(media: str | None) -> str:
    if media == ONE_PIECE_MEDIA_ANIME:
        return "episodio"
    return "capítulo"
