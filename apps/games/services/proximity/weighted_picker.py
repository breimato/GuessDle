import random

from apps.games.models import GameItem
from apps.games.services.proximity.game_config import LOL_LEGACY_WEIGHT, LOL_RECENT_WEIGHT, LOL_RECENT_YEAR, lol_release_year


def pick_weighted_item(items: list[GameItem], rng: random.Random) -> GameItem | None:
    if not items:
        return None
    weights = []
    for item in items:
        release_year = lol_release_year(item.data)
        weight = LOL_RECENT_WEIGHT if release_year and int(release_year) >= LOL_RECENT_YEAR else LOL_LEGACY_WEIGHT
        weights.append(weight)
    return rng.choices(items, weights=weights, k=1)[0]
