from django.db.models import QuerySet

from apps.games.models import Game, GameItem, GameMode
from apps.games.services.proximity.pool_service import ProximityPoolService


class SilhouettePoolService:
    def __init__(self, game: Game, mode: GameMode, filter_config: dict):
        self.game = game
        self.mode = mode
        self.filter_config = filter_config
        self._proximity_pool = ProximityPoolService(game, mode, filter_config)

    def item_queryset(self) -> QuerySet[GameItem]:
        base = self._proximity_pool.item_queryset()
        valid_ids = [item.pk for item in base if item.get_image_url()]
        return GameItem.objects.filter(pk__in=valid_ids)

    def has_playable_pool(self) -> bool:
        return self.item_queryset().exists()
