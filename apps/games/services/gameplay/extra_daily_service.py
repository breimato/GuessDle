"""Service managing extra daily play sessions, including validation, point deduction, and creation."""

from django.contrib.auth.models import User
from django.utils import timezone

from apps.games.models import Game, ExtraDailyPlay
from apps.games.services.gameplay.target_service import TargetService
from apps.accounts.services.score_service import ScoreService


class ExtraDailyService:
    """Manages rules and actions for initializing extra daily play sessions with points-wagering."""

    MAX_EXTRAS_PER_DAY = 2

    def __init__(self, user: User, game: Game):
        """Initialize extra daily service."""

        self.user = user
        self.game = game

    def count_today(self) -> int:
        """Count the number of extra play sessions started by the user in this game today."""

        today = timezone.localdate()
        return ExtraDailyPlay.objects.filter(
            user=self.user,
            game=self.game,
            created_at__date=today,
        ).count()

    def max_reached(self) -> bool:
        """Check if the user has reached the daily limit of extra play sessions."""

        return self.count_today() >= self.MAX_EXTRAS_PER_DAY

    def start_extra_play(self, bet_amount: float) -> ExtraDailyPlay:
        """Validate bet amount, deduct points from score, select random target, and create extra play session."""

        if bet_amount <= 0:
            raise ValueError("The bet must be greater than zero.")

        if self.max_reached():
            raise ValueError("You have already played the maximum number of extra games today.")

        score_service = ScoreService(self.user, self.game)
        current_points = score_service.score_obj.elo

        if current_points < bet_amount:
            raise ValueError("You do not have enough points for that bet.")

        score_service.score_obj.elo = current_points - bet_amount
        score_service.score_obj.save(update_fields=["elo"])

        target = TargetService(self.game, self.user).get_random_item()
        return ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            target=target,
            bet_amount=bet_amount,
        )
