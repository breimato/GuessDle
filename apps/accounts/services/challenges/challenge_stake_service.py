from django.db.models import Q, Sum

from apps.accounts.models import Challenge, GameElo


class ChallengeStakeService:
    def __init__(self, game, mode=None):
        self.game = game
        self.mode = mode

    def available_points(self, user) -> float:
        total_points = self._total_points(user)
        held_points = self._held_points(user)
        return max(0.0, total_points - held_points)

    def max_stake_between(self, challenger, opponent) -> float:
        challenger_available = self.available_points(challenger)
        opponent_available = self.available_points(opponent)
        return min(challenger_available, opponent_available)

    def can_lock_stake(self, user, amount: float) -> bool:
        return amount > 0 and self.available_points(user) >= amount

    def _total_points(self, user) -> float:
        score = self._elo_queryset().filter(user=user).first()
        if score is None:
            return 0.0
        return float(score.elo)

    def _held_points(self, user) -> float:
        held = self._challenge_queryset().filter(
            Q(challenger=user) | Q(opponent=user)
        ).aggregate(total=Sum("stake_points"))
        return float(held["total"] or 0.0)

    def _elo_queryset(self):
        queryset = GameElo.objects.filter(game=self.game)
        if self.mode is None:
            return queryset.filter(mode__isnull=True)
        return queryset.filter(mode=self.mode)

    def _challenge_queryset(self):
        queryset = Challenge.objects.filter(
            game=self.game,
            accepted=True,
            completed=False,
            stake_settled=False,
        )
        if self.mode is None:
            return queryset.filter(mode__isnull=True)
        return queryset.filter(mode=self.mode)
