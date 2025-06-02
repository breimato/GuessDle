# apps/games/services/gameplay/result_updater.py

from django.db.models import Count, Avg
from apps.games.attempts import build_attempts  # si lo necesitas, aunque no en este caso
from apps.games.models import ExtraDailyPlay, GameAttempt
from .play_session_service import PlaySessionService
from apps.accounts.services.elo import Elo


class ResultUpdater:
    """
    Antes usábamos GameResult con daily_target/extra_play/challenge,
    pero esos campos ya no existen. Ahora simplemente contamos intentos
    en la PlaySession y actualizamos el Elo directamente.
    """

    def __init__(self, game, user):
        self.game = game
        self.user = user

    def update_for_game(self, *, daily_target=None, extra_play=None, challenge=None):
        """
        - daily_target / extra_play / challenge: contextos mutuamente excluyentes.
        - Obtenemos la PlaySession, contamos sus intentos, y actualizamos Elo.
        - No usamos GameResult; si quieres registrar resultados en BD, crea un
          modelo PlayResult que apunte a PlaySession.
        """
        # 1️⃣ Validación de contextos
        contexts = [daily_target, extra_play, challenge]
        if sum(bool(x) for x in contexts) != 1:
            raise ValueError("Debes indicar exactamente un contexto (daily, extra o challenge).")

        # 2️⃣ Obtener o crear la PlaySession adecuada
        session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        # 3️⃣ Contar intentos de esa sesión
        attempts_count = GameAttempt.objects.filter(session=session).count()

        # 4️⃣ Si extra_play, manejamos apuesta y ELO especial
        elo_service = Elo(self.user, self.game)

        if extra_play:
            # Recuperar la apuesta real desde la instancia de ExtraDailyPlay
            bet_amount = ExtraDailyPlay.objects.filter(pk=extra_play.id, user=self.user).get().bet_amount

            # Verificamos si hay otros jugadores que también hayan jugado esta partida extra
            # (es decir, si existen sesiones / GameAttempt de otros usuarios para el mismo game/extra_play).
            hay_otros = GameAttempt.objects.filter(
                session__session_type="EXTRA",
                session__reference_id=extra_play.id
            ).exclude(user=self.user).exists()

            if hay_otros:
                # Comparamos contra la media global de intentos (sobre todas las sesiones EXTRA de este juego)
                # NOTA: aquí asumimos que en Elo._did_win() espera recibir “intentos_count” y compararlo con media global
                result_flag = elo_service._did_win(attempts_count)
            else:
                # Si eres el único jugador hasta ahora, compáralo contigo mismo históricamente
                user_avg = (
                    GameAttempt.objects
                    .filter(
                        session__session_type="EXTRA",
                        session__game=self.game,
                        user=self.user
                    )
                    .annotate(attempts_count=Count("pk"))
                    .aggregate(avg=Avg("attempts_count"))["avg"]
                )
                # Si no hay historico (user_avg es None), cuentas como victoria
                result_flag = 1 if user_avg is None or attempts_count < user_avg else 0

            # Ganancia/pérdida de ELO: 1.5× apuesta si ganas, 0 si pierdes
            gain = bet_amount * (1.5 if result_flag == 1 else 0)
            elo_service.elo_obj.elo += gain
            elo_service.elo_obj.partidas += 1
            elo_service.elo_obj.save(update_fields=["elo", "partidas"])

        else:
            # Flujo normal de ELO basado en “intentos_count” y media histórica
            elo_service.update(attempts_count)
