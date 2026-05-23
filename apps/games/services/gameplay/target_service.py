"""Service to query, construct, and retrieve targets for daily play and challenges."""

import secrets
from datetime import timedelta
from django.utils import timezone
from apps.games.models import DailyTarget, PlaySession, PlaySessionType, GameAttempt, GameItem


class TargetService:
    """Manages target item retrieval and checks if daily challenges have been completed."""

    def __init__(self, game, user):
        """Initialize target service."""

        self.game = game
        self.user = user
        self.is_team_account = getattr(getattr(user, "profile", None), "is_team_account", False)

    def get_target_for_today(self):
        """Retrieve the DailyTarget record designated for today's date."""

        today = timezone.localdate()
        return DailyTarget.objects.filter(
            game=self.game,
            date=today,
            is_team=self.is_team_account,
            target__deleted=False
        ).select_related("target").first()

    def get_yesterday_target(self, today_date=None):
        """Retrieve the DailyTarget record designated for yesterday's date."""

        today_date = today_date or timezone.localdate()
        yesterday = today_date - timedelta(days=1)
        return DailyTarget.objects.filter(
            game=self.game,
            date=yesterday,
            is_team=self.is_team_account
        ).select_related("target").first()

    def get_current_target(self):
        """Retrieve the current target for this game and user context."""

        return DailyTarget.get_current(self.game, self.user)

    def get_random_item(self):
        """Select and return a random active GameItem belonging to this game."""

        items = list(GameItem.objects.filter(game=self.game, deleted=False))
        if not items:
            raise ValueError("No items available for this game.")
        return secrets.choice(items)

    def is_daily_resolved(self):
        """Check if today's daily target challenge has already been successfully solved by the user."""

        today = timezone.localdate()
        daily_target = DailyTarget.objects.filter(
            game=self.game,
            date=today,
            is_team=self.is_team_account
        ).select_related("target").first()

        if not daily_target:
            return False

        play_session = PlaySession.objects.filter(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=daily_target.id
        ).first()

        if not play_session:
            return False

        return GameAttempt.objects.filter(session=play_session, is_correct=True).exists()
