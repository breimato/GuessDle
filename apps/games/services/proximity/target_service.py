import secrets

from django.utils import timezone

from apps.games.models import Game, GameMode, ProximityDailyAssignment, ProximityPrompt
from apps.games.services.proximity.answer_resolver import (
    ProximityAnswerResolver,
    resolve_assignment_answer,
)
from apps.games.services.proximity.game_config import EVENT_POOL_WEIGHT, proximity_game_kind
from apps.games.services.proximity.pool_service import ProximityPoolService
from apps.games.services.proximity.weighted_picker import pick_weighted_item


class ProximityTargetService:
    def __init__(self, game: Game, user, mode: GameMode):
        self.game = game
        self.user = user
        self.mode = mode
        self.is_team = bool(
            getattr(getattr(user, "profile", None), "is_team_account", False)
        )
        self.resolver = ProximityAnswerResolver(game)

    def get_today_assignment(self) -> ProximityDailyAssignment | None:
        return ProximityDailyAssignment.objects.filter(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=self.is_team,
        ).select_related("target_item", "proximity_prompt").first()

    def ensure_assignment(self, filter_config: dict) -> ProximityDailyAssignment | None:
        existing = self.get_today_assignment()
        if existing:
            if existing.filter_config != filter_config:
                existing.delete()
            else:
                answer = resolve_assignment_answer(self.game, existing)
                if existing.answer_value != answer:
                    existing.answer_value = answer
                    existing.save(update_fields=["answer_value"])
                return existing

        pool = ProximityPoolService(self.game, self.mode, filter_config)
        if not pool.has_playable_pool():
            return None

        rng = secrets.SystemRandom()
        resolver = ProximityAnswerResolver(self.game, media=filter_config.get("media"))
        target_item, prompt = self._pick_target(pool, rng)
        if target_item is None and prompt is None:
            return None

        answer = (
            resolver.resolve_item(target_item)
            if target_item
            else resolver.resolve_prompt(prompt)
        )
        if answer is None:
            return None

        return ProximityDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=self.is_team,
            filter_config=filter_config,
            target_item=target_item,
            proximity_prompt=prompt,
            answer_value=answer,
        )

    def _pick_target(self, pool: ProximityPoolService, rng: secrets.SystemRandom):
        items = list(pool.item_queryset())
        prompts = list(pool.prompt_queryset())

        kind = proximity_game_kind(self.game)
        if kind == "one_piece" and prompts and items:
            if rng.random() < EVENT_POOL_WEIGHT:
                return None, rng.choice(prompts)
            item = rng.choice(items)
            return item, None

        if kind == "lol" and items:
            return pick_weighted_item(items, rng), None

        if items:
            return rng.choice(items), None
        if prompts:
            return None, rng.choice(prompts)
        return None, None
