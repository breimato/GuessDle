import hashlib

from apps.games.models import GameItem

SILHOUETTE_ANCHORS = ("tl", "tr", "bl", "br")


def resolve_anchor(target_item: GameItem, assignment_date, user_id: int) -> str:
    payload = f"{target_item.pk}:{assignment_date}:{user_id}"
    digest = hashlib.sha256(payload.encode()).hexdigest()
    index = int(digest, 16) % len(SILHOUETTE_ANCHORS)
    return SILHOUETTE_ANCHORS[index]
