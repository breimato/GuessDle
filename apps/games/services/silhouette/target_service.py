import secrets

from django.utils import timezone

from apps.games.models import Game, GameMode, SilhouetteDailyAssignment
from apps.games.services.silhouette.anchor_service import resolve_anchor
from apps.games.services.silhouette.pool_service import SilhouettePoolService


class SilhouetteTargetService:
    def __init__(self, game: Game, user, mode: GameMode):
        self.game = game
        self.user = user
        self.mode = mode
        self.is_team = SilhouetteTargetService._is_team_user(user)

    @staticmethod
    def _is_team_user(user) -> bool:
        return bool(getattr(getattr(user, "profile", None), "is_team_account", False))

    def get_today_assignment(self) -> SilhouetteDailyAssignment | None:
        return SilhouetteDailyAssignment.objects.filter(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            is_team=self.is_team,
        ).select_related("target_item").first()

    def ensure_assignment(self, filter_config: dict) -> SilhouetteDailyAssignment | None:
        existing = self.get_today_assignment()
        if existing:
            if existing.filter_config != filter_config:
                existing.delete()
            else:
                return existing

        pool = SilhouettePoolService(self.game, self.mode, filter_config)
        items = list(pool.item_queryset())
        if not items:
            return None

        rng = secrets.SystemRandom()
        target_item = rng.choice(items)
        assignment_date = timezone.localdate()
        anchor = resolve_anchor(target_item, assignment_date, self.user.pk)

        return SilhouetteDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=assignment_date,
            is_team=self.is_team,
            filter_config=filter_config,
            target_item=target_item,
            anchor=anchor,
        )
