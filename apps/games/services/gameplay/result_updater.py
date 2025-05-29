from apps.games.models import GameAttempt, GameResult
from apps.accounts.services.elo import Elo


class ResultUpdater:
    def __init__(self, game, user):
        self.game = game
        self.user = user

    def update_for_daily(self, daily_target):
        result, created = GameResult.objects.get_or_create(
            user=self.user,
            game=self.game,
            daily_target=daily_target,
            defaults={
                "attempts": GameAttempt.objects.filter(
                    user=self.user,
                    daily_target=daily_target,
                ).count()
            },
        )
        if created:
            Elo(self.user, self.game).update(result.attempts)
