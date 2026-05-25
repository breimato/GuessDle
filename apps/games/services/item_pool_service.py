import secrets

from django.db.models import Q, QuerySet

from apps.games.models import Game, GameItem, GameMode
from apps.games.services.generation_utils import GENERATION_MAX_IDS


class ItemPoolService:
    def __init__(self, game: Game, mode: GameMode | None = None):
        self.game = game
        self.mode = mode

    def get_queryset(self) -> QuerySet[GameItem]:
        queryset = GameItem.objects.filter(game=self.game, deleted=False)
        if not self.mode:
            return queryset
        clause = self._build_q(self.mode.item_filter or {})
        if clause is not None:
            queryset = queryset.filter(clause)
        return queryset

    def pick_random(self) -> GameItem | None:
        queryset = self.get_queryset()
        count = queryset.count()
        if count == 0:
            return None
        return queryset[secrets.randbelow(count)]

    def contains_name(self, name: str) -> bool:
        return self.get_queryset().filter(name__iexact=name).exists()

    def _build_q(self, item_filter: dict) -> Q | None:
        if not item_filter:
            return None
        clause = Q()
        for key, value in item_filter.items():
            if key == "generacion__lte":
                clause &= self._generacion_lte_q(int(value))
            elif key == "generacion__gte":
                clause &= self._generacion_gte_q(int(value))
            elif key == "generacion":
                clause &= self._generacion_exact_q(int(value))
            elif key == "id__lte":
                clause &= Q(data__id__lte=int(value))
            elif key == "id__gte":
                clause &= Q(data__id__gte=int(value))
        return clause

    @staticmethod
    def _generacion_lte_q(max_generation: int) -> Q:
        max_id = GENERATION_MAX_IDS[min(max_generation, len(GENERATION_MAX_IDS)) - 1]
        return Q(data__generacion__lte=max_generation) | Q(data__id__lte=max_id)

    @staticmethod
    def _generacion_gte_q(min_generation: int) -> Q:
        if min_generation <= 1:
            return Q()
        min_id = GENERATION_MAX_IDS[min_generation - 2] + 1
        return Q(data__generacion__gte=min_generation) | Q(data__id__gte=min_id)

    @staticmethod
    def _generacion_exact_q(generation: int) -> Q:
        if generation <= 1:
            return Q(data__generacion=1) | Q(data__id__lte=GENERATION_MAX_IDS[0])
        lower = GENERATION_MAX_IDS[generation - 2] + 1
        upper = GENERATION_MAX_IDS[generation - 1]
        return Q(data__generacion=generation) | Q(
            data__id__gte=lower, data__id__lte=upper
        )
