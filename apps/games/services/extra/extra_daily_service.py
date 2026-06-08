from django.contrib.auth.models import User
from django.utils import timezone

from apps.accounts.services.wallet.score_service import ScoreService
from apps.games.models import ExtraDailyPlay, Game
from apps.games.services.daily.target_service import TargetService


class ExtraDailyService:
    MAX_EXTRAS_PER_DAY = 2

    def __init__(self, user: User, game: Game, mode=None):
        self.user = user
        self.game = game
        self.mode = mode

    def _mode_filter(self):
        if self.mode:
            return {"mode": self.mode}
        return {"mode__isnull": True}

    def count_today(self) -> int:
        today = timezone.localdate()
        return ExtraDailyPlay.objects.filter(
            user=self.user,
            game=self.game,
            created_at__date=today,
            **self._mode_filter(),
        ).count()

    def max_reached(self) -> bool:
        return self.count_today() >= self.MAX_EXTRAS_PER_DAY

    def start_extra_play(self, bet_amount: float) -> ExtraDailyPlay:
        if bet_amount <= 0:
            raise ValueError("La apuesta debe ser mayor que cero.")

        if self.max_reached():
            raise ValueError(
                "Ya has jugado el máximo de partidas extra de hoy para este juego."
            )

        score_service = ScoreService(self.user, self.game, mode=self.mode)
        current_points = score_service.score_obj.elo

        if current_points < bet_amount:
            raise ValueError(
                "No tienes puntos suficientes en este juego para esa apuesta."
            )

        score_service.score_obj.elo = current_points - bet_amount
        score_service.score_obj.save(update_fields=["elo"])

        target = TargetService(self.game, self.user, mode=self.mode).get_random_item()
        return ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            target=target,
            bet_amount=bet_amount,
            mode=self.mode,
        )
