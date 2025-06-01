from datetime import date

from django.contrib.auth.models import User
from django.utils.timezone import now, localtime
from django.utils import timezone


from apps.games.models import Game, ExtraDailyPlay
from apps.games.services.gameplay.target_service import TargetService
from apps.accounts.services.elo import Elo


class ExtraDailyService:
    """
    Encapsula TODA la lógica relacionada con partidas extra diarias:
    - contar cuántas lleva
    - validar y registrar apuestas
    - crear la ExtraDailyPlay
    """

    MAX_EXTRAS_PER_DAY = 2

    def __init__(self, user: User, game: Game):
        self.user = user
        self.game = game

    # ---------- Consulta ---------- #
    def count_today(self) -> int:
        # Usamos localdate() para comparar con la fecha local (Europe/Madrid)
        today = timezone.localdate()
        return ExtraDailyPlay.objects.filter(
            user=self.user,
            game=self.game,
            created_at__date=today,
        ).count()

    def max_reached(self) -> bool:
        return self.count_today() >= self.MAX_EXTRAS_PER_DAY

    # ---------- Creación ---------- #
    def start_extra_play(self, bet_amount: float) -> ExtraDailyPlay:
        if bet_amount <= 0:
            raise ValueError("La apuesta debe ser mayor que cero.")

        if self.max_reached():
            raise ValueError("Ya has jugado el máximo de partidas extra hoy.")

        elo = Elo(self.user, self.game)
        if elo.elo_obj.elo < bet_amount:
            raise ValueError("No tienes suficiente ELO para esa apuesta.")

        # Restar ELO
        elo.elo_obj.elo -= bet_amount
        elo.elo_obj.save(update_fields=["elo"])

        # Elegir target aleatorio y crear partida extra
        target = TargetService(self.game, self.user).get_random_item()
        return ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            target=target,
            bet_amount=bet_amount,
        )
