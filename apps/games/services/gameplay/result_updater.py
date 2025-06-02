# apps/games/services/gameplay/result_updater.py

from django.db.models import Count, Avg
from apps.games.models import ExtraDailyPlay, GameAttempt
from .play_session_service import PlaySessionService
from apps.accounts.services.score_service import ScoreService


class ResultUpdater:
    """
    Ya NO usamos Elo.  Cada partida otorga puntos según la tabla ScoringRule
    y, en el caso de partidas EXTRA, puede añadirse un bonus según la apuesta.
    """

    def __init__(self, game, user):
        self.game = game
        self.user = user

    # ------------------------------------------------------------------ #
    def update_for_game(self, *, daily_target=None, extra_play=None, challenge=None):
        """
        Recibe exactamente un contexto (daily_target, extra_play o challenge).
        1. Localiza la PlaySession (o la crea).
        2. Cuenta los intentos.
        3. Aplica puntos usando ScoreService.
        4. Si es EXTRA → calcula bonus por apuesta y lo añade si “gana”.
        """

        # 1️⃣ Validación de contextos (exactamente uno)
        contexts = [daily_target, extra_play, challenge]
        if sum(bool(x) for x in contexts) != 1:
            raise ValueError("Debes indicar exactamente un contexto (daily, extra o challenge).")

        # 2️⃣ Obtener / crear PlaySession
        session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        # 3️⃣ Contar los intentos de la sesión
        attempts_count = GameAttempt.objects.filter(session=session).count()

        # 4️⃣ Añadir puntos base según la tabla ScoringRule
        score_service = ScoreService(self.user, self.game)
        base_pts = score_service.add_points_for_attempts(attempts_count)

        # ------------------------------------------------------------------ #
        # BONUS por apuesta (sólo partidas EXTRA)
        if extra_play:
            # Apuesta del usuario
            bet_amount = ExtraDailyPlay.objects.get(pk=extra_play.id, user=self.user).bet_amount

            # ¿Hay otros jugadores en la misma partida extra?
            hay_otros = GameAttempt.objects.filter(
                session__session_type="EXTRA",
                session__reference_id=extra_play.id
            ).exclude(user=self.user).exists()

            # Determinar si “gana” la apuesta
            if hay_otros:
                # Comparar contra la media global de intentos de otros en esta EXTRA
                global_avg = (
                    GameAttempt.objects
                    .filter(
                        session__session_type="EXTRA",
                        session__reference_id=extra_play.id,
                        is_correct=True
                    )
                    .aggregate(avg=Avg("session__attempts__count"))  # intentos por sesión
                    ["avg"]
                )
                result_flag = 1 if global_avg is None or attempts_count < global_avg else 0
            else:
                # Único jugador: comparar contra tu propia media histórica de EXTRA
                user_avg = (
                    GameAttempt.objects
                    .filter(
                        session__session_type="EXTRA",
                        session__game=self.game,
                        user=self.user,
                        is_correct=True
                    )
                    .annotate(attempts_count=Count("pk"))
                    .aggregate(avg=Avg("attempts_count"))["avg"]
                )
                result_flag = 1 if user_avg is None or attempts_count < user_avg else 0

            # Bonus: 1.5 × apuesta si gana, 0 si pierde
            bonus_pts = bet_amount * 1.5 if result_flag else 0
            if bonus_pts:
                score_service.score_obj.elo += bonus_pts
                score_service.score_obj.save(update_fields=("elo",))

        # ------------------------------------------------------------------ #
        # Devuelve los puntos totales sumados (base + bonus opcional)
        return base_pts + (bonus_pts if extra_play else 0)
