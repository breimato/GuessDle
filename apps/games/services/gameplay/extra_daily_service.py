# apps/games/services/gameplay/extra_daily_service.py

from datetime import date

from django.contrib.auth.models import User
from django.utils import timezone  # IMPORT CORRECTO: usar django.utils.timezone

from apps.games.models import Game, ExtraDailyPlay
from apps.games.services.gameplay.target_service import TargetService
from apps.accounts.services.score_service import ScoreService


class ExtraDailyService:
    """
    Encapsula TODA la lógica relacionada con partidas extra diarias:
      - contar cuántas lleva el usuario hoy
      - validar y restar apuesta de sus puntos
      - crear la ExtraDailyPlay
    """

    MAX_EXTRAS_PER_DAY = 2

    def __init__(self, user: User, game: Game):
        self.user = user
        self.game = game

    # ---------- Consultas ---------- #
    def count_today(self) -> int:
        """
        Devuelve cuántas partidas extra ha iniciado este usuario
        en este juego hoy (fecha local).
        """
        today = timezone.localdate()  # ahora sí es el método de django.utils.timezone
        return ExtraDailyPlay.objects.filter(
            user=self.user,
            game=self.game,
            created_at__date=today,
        ).count()

    def max_reached(self) -> bool:
        """
        True si ya alcanzó el máximo de partidas extra hoy.
        """
        return self.count_today() >= self.MAX_EXTRAS_PER_DAY

    # ---------- Creación ---------- #
    def start_extra_play(self, bet_amount: float) -> ExtraDailyPlay:
        """
        Valida la apuesta y crea la partida extra con la apuesta registrada.
        Resta los puntos (antes ELO) de ScoreService.
        """
        if bet_amount <= 0:
            raise ValueError("La apuesta debe ser mayor que cero.")

        if self.max_reached():
            raise ValueError("Ya has jugado el máximo de partidas extra hoy.")

        # Reemplazamos Elo por ScoreService
        score_service = ScoreService(self.user, self.game)
        current_points = score_service.score_obj.elo

        if current_points < bet_amount:
            raise ValueError("No tienes suficientes puntos para esa apuesta.")

        # Restar puntos
        score_service.score_obj.elo = current_points - bet_amount
        score_service.score_obj.save(update_fields=["elo"])

        # Elegir target aleatorio y crear partida extra
        target = TargetService(self.game, self.user).get_random_item()
        return ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            target=target,
            bet_amount=bet_amount,
        )
