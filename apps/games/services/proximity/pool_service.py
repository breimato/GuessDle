from django.db.models import Q, QuerySet

from apps.games.models import Game, GameItem, GameMode, ProximityPrompt
from apps.games.services.catalog.generation_utils import GENERATION_MAX_IDS
from apps.games.services.proximity.answer_resolver import ProximityAnswerResolver
from apps.games.services.proximity.filter_service import slugify_arc_label
from apps.games.services.proximity.game_config import proximity_game_kind


class ProximityPoolService:
    def __init__(self, game: Game, mode: GameMode, filter_config: dict):
        self.game = game
        self.mode = mode
        self.filter_config = filter_config
        self.resolver = ProximityAnswerResolver(
            game,
            media=filter_config.get("media"),
        )

    def item_queryset(self) -> QuerySet[GameItem]:
        queryset = GameItem.objects.filter(game=self.game, deleted=False)
        clause = self._build_item_q()
        if clause is not None:
            queryset = queryset.filter(clause)
        valid_ids = []
        for item in queryset.iterator():
            if self.resolver.resolve_item(item) is not None:
                valid_ids.append(item.pk)
        return GameItem.objects.filter(pk__in=valid_ids)

    def prompt_queryset(self) -> QuerySet[ProximityPrompt]:
        if proximity_game_kind(self.game) != "one_piece":
            return ProximityPrompt.objects.none()
        queryset = ProximityPrompt.objects.filter(game=self.game, active=True)
        arcs = set(self.filter_config.get("arcs") or [])
        if arcs:
            queryset = [prompt for prompt in queryset if arcs.intersection(prompt.arcs or [])]
        else:
            queryset = list(queryset)
        if self.filter_config.get("media") == "anime":
            queryset = [
                prompt
                for prompt in queryset
                if self.resolver.resolve_prompt(prompt) is not None
            ]
        ids = [prompt.pk for prompt in queryset]
        return ProximityPrompt.objects.filter(pk__in=ids)

    def has_playable_pool(self) -> bool:
        return self.item_queryset().exists() or self.prompt_queryset().exists()

    def _build_item_q(self) -> Q | None:
        kind = proximity_game_kind(self.game)
        if kind == "pokemon":
            return self._pokemon_generations_q()
        if kind == "lol":
            return self._lol_years_q()
        if kind == "one_piece":
            return self._one_piece_arcs_q()
        return None

    def _pokemon_generations_q(self) -> Q:
        generations = self.filter_config.get("generations") or [1, 2, 3]
        clause = Q()
        for generation in generations:
            generation = int(generation)
            if generation <= 1:
                clause |= Q(data__generacion=1) | Q(data__id__lte=GENERATION_MAX_IDS[0])
            else:
                lower = GENERATION_MAX_IDS[generation - 2] + 1
                upper = GENERATION_MAX_IDS[generation - 1]
                clause |= Q(data__generacion=generation) | Q(
                    data__id__gte=lower, data__id__lte=upper
                )
        return clause

    def _lol_years_q(self) -> Q:
        years = self._lol_selected_years()
        return Q(data__releaseDate__in=years) | Q(data__Año__in=years)

    def _lol_selected_years(self) -> list[int]:
        years = self.filter_config.get("years")
        if years:
            return [int(year) for year in years]
        year_min = self.filter_config.get("year_min")
        year_max = self.filter_config.get("year_max")
        if year_min is not None and year_max is not None:
            return list(range(int(year_min), int(year_max) + 1))
        return list(range(2012, 2027))

    def _one_piece_arcs_q(self) -> Q | None:
        arcs = self.filter_config.get("arcs") or []
        if not arcs:
            return None
        clause = Q()
        for arc_slug in arcs:
            clause |= Q(data__arco_slug=arc_slug)
            clause |= Q(data__arco_de_primera_aparicion__icontains=arc_slug.replace("_", " "))
        return clause

    @staticmethod
    def arc_slug_from_item_data(data: dict) -> str | None:
        if not data:
            return None
        if data.get("arco_slug"):
            return str(data["arco_slug"])
        label = data.get("arco de primera aparición") or data.get("arco")
        if not label:
            return None
        return slugify_arc_label(str(label))
