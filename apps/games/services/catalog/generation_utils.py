from apps.games.constants import is_pokemon_game
from apps.games.services.catalog.one_piece_episode_utils import enrich_one_piece_episode

GENERATION_MAX_IDS = (151, 251, 386, 493, 649, 721, 809, 905, 1025)


def generation_from_national_id(national_id: int) -> int:
    if national_id <= 0:
        return 1
    for index, upper in enumerate(GENERATION_MAX_IDS, start=1):
        if national_id <= upper:
            return index
    return len(GENERATION_MAX_IDS)


def _is_one_piece_item_data(data: dict) -> bool:
    return data.get("capítulo") is not None or data.get("capitulo") is not None


def enrich_item_data(data: dict, game=None) -> dict:
    enriched = dict(data)

    if game is not None and is_pokemon_game(game.slug):
        item_id = enriched.get("id")
        if item_id is not None and "generacion" not in enriched:
            enriched["generacion"] = generation_from_national_id(int(item_id))
        return enriched

    enriched.pop("generacion", None)
    if _is_one_piece_item_data(enriched):
        enriched = enrich_one_piece_episode(enriched)
    return enriched
