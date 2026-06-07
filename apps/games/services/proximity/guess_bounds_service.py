from apps.games.models import Game, GameMode, ProximityDailyAssignment
from apps.games.services.catalog.generation_utils import GENERATION_MAX_IDS
from apps.games.services.proximity.answer_resolver import ProximityAnswerResolver
from apps.games.services.proximity.game_config import proximity_game_kind
from apps.games.services.proximity.pool_service import ProximityPoolService

DISCRETE_MAX = 25
SLIDER_MAX = 150
SEGMENT_BLOCK_SIZE = 100


def picker_mode_for_span(span: int) -> str:
    if span <= DISCRETE_MAX:
        return "discrete"
    if span <= SLIDER_MAX:
        return "slider"
    return "segmented"


class ProximityGuessBoundsService:
    def __init__(self, game: Game, mode: GameMode, assignment: ProximityDailyAssignment):
        self.game = game
        self.mode = mode
        self.assignment = assignment
        self.filter_config = assignment.filter_config or {}
        self.kind = proximity_game_kind(game)

    def resolve(self) -> dict:
        if self.kind == "lol":
            return self._lol_bounds(picker_mode="lol_champions")
        if self.kind == "pokemon":
            return self._pokemon_bounds(picker_mode="pokemon_pokedex")
        if self.kind == "one_piece":
            return self._pool_bounds(picker_mode="one_piece_scroll")
        return self._pool_bounds()

    def _lol_bounds(self, *, picker_mode: str | None = None) -> dict:
        pool = ProximityPoolService(self.game, self.mode, self.filter_config)
        years = sorted(set(pool._lol_selected_years()))
        if not years:
            years = [2012]
        return self._build_bounds(
            guess_min=years[0],
            guess_max=years[-1],
            discrete_values=years,
            picker_mode=picker_mode,
        )

    def _pokemon_bounds(self, *, picker_mode: str | None = None) -> dict:
        generations = self.filter_config.get("generations") or [1, 2, 3]
        guess_min = 1
        guess_max = GENERATION_MAX_IDS[0]
        for generation in generations:
            generation = int(generation)
            if generation <= 1:
                upper = GENERATION_MAX_IDS[0]
            else:
                upper = GENERATION_MAX_IDS[min(generation, len(GENERATION_MAX_IDS)) - 1]
            guess_max = max(guess_max, upper)
        return self._build_bounds(
            guess_min=guess_min,
            guess_max=guess_max,
            picker_mode=picker_mode,
        )

    def _pool_bounds(self, *, picker_mode: str | None = None) -> dict:
        pool = ProximityPoolService(self.game, self.mode, self.filter_config)
        resolver = pool.resolver
        values: list[int] = []
        for item in pool.item_queryset().iterator():
            answer = resolver.resolve_item(item)
            if answer is not None:
                values.append(answer)
        for prompt in pool.prompt_queryset().iterator():
            answer = resolver.resolve_prompt(prompt)
            if answer is not None:
                values.append(answer)
        if not values:
            return self._build_bounds(guess_min=1, guess_max=1, picker_mode=picker_mode)
        return self._build_bounds(
            guess_min=min(values),
            guess_max=max(values),
            picker_mode=picker_mode,
        )

    def _build_bounds(
        self,
        *,
        guess_min: int,
        guess_max: int,
        discrete_values: list[int] | None = None,
        picker_mode: str | None = None,
    ) -> dict:
        if guess_min > guess_max:
            guess_min, guess_max = guess_max, guess_min
        span = guess_max - guess_min + 1
        mode = picker_mode or picker_mode_for_span(span)
        payload = {
            "guess_min": guess_min,
            "guess_max": guess_max,
            "guess_step": 1,
            "picker_mode": mode,
            "segment_block_size": SEGMENT_BLOCK_SIZE,
        }
        if discrete_values is not None:
            payload["discrete_values"] = discrete_values
        elif mode == "discrete":
            payload["discrete_values"] = list(range(guess_min, guess_max + 1))
        return payload
