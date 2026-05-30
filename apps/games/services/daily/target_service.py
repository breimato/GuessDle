from datetime import timedelta

from django.utils import timezone

from apps.games.models import DailyTarget, GameAttempt, GameModePlayType, PlaySession, PlaySessionType
from apps.games.services.catalog.item_pool_service import ItemPoolService


class TargetService:
    def __init__(self, game, user, mode=None):
        self.game = game
        self.user = user
        self.mode = mode
        self.is_team_account = getattr(
            getattr(user, "profile", None), "is_team_account", False
        )

    def _mode_filter(self):
        if self.mode:
            return {"mode": self.mode}
        return {"mode__isnull": True}

    def get_target_for_today(self):
        return (
            DailyTarget.objects.filter(
                game=self.game,
                date=timezone.localdate(),
                is_team=self.is_team_account,
                target__deleted=False,
                **self._mode_filter(),
            )
            .select_related("target", "mode")
            .first()
        )

    def get_yesterday_target(self, today_date=None):
        today_date = today_date or timezone.localdate()
        yesterday = today_date - timedelta(days=1)
        return (
            DailyTarget.objects.filter(
                game=self.game,
                date=yesterday,
                is_team=self.is_team_account,
                **self._mode_filter(),
            )
            .select_related("target", "mode")
            .first()
        )

    def get_current_target(self):
        return DailyTarget.get_current(self.game, self.user, mode=self.mode)

    def get_random_item(self):
        item = ItemPoolService(self.game, self.mode).pick_random()
        if not item:
            raise ValueError("No items available for this game.")
        return item

    def is_daily_resolved(self):
        daily_target = self.get_target_for_today()
        if not daily_target:
            return False
        play_session = PlaySession.objects.filter(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=daily_target.id,
        ).first()
        if not play_session:
            return False
        return GameAttempt.objects.filter(
            session=play_session, is_correct=True
        ).exists()

    def has_any_unresolved_mode(self):
        from apps.games.services.catalog.mode_resolver import ModeResolver

        resolver = ModeResolver(self.game)
        wordle_modes = [
            mode
            for mode in resolver.active_modes()
            if mode.play_type != GameModePlayType.ROSCO
        ]
        if not wordle_modes:
            if resolver.has_modes():
                return False
            return not self.is_daily_resolved()
        return any(
            not TargetService(self.game, self.user, mode=mode).is_daily_resolved()
            for mode in wordle_modes
        )
