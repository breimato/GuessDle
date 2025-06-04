from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Count, Avg, Q, Sum
from apps.games.models import ScoringRule, GameAttempt, PlaySessionType
from apps.accounts.models import GameElo

class ScoreService:
    """
    Actualiza y consulta los puntos de un usuario en un juego.
    Usa la tabla GameElo para no crear otra (puedes renombrarla luego).
    """
    def __init__(self, user, game):
        self.user  = user
        self.game  = game
        self.score_obj, _ = GameElo.objects.get_or_create(user=user, game=game)

    # ---------- API pública ----------
    def add_points_for_attempts(self, attempts_count: int) -> int:
        """Devuelve los puntos sumados y actualiza la tabla."""
        pts = self._points_for_attempts(attempts_count)
        self.score_obj.elo += pts
        self.score_obj.partidas += 1
        self.score_obj.save(update_fields=("elo", "partidas"))
        return pts

    def get_user_average_attempts(self) -> float | None:
        """
        Promedio de intentos hechos por el usuario en sesiones EXTRA del juego.
        Incluye sesiones no completadas. La media es (intentos totales) / (partidas completadas).
        Si no hay partidas completadas, devuelve None.
        """
        # Todas las sesiones del usuario en este juego
        sessions = (
            self.user.play_sessions
            .filter(game=self.game)
        )

        # Intentos totales (todas las sessions)
        total_tries = (
            GameAttempt.objects
            .filter(session__in=sessions)
            .count()
        )

        # Partidas completadas: sessions donde hay al menos 1 intento correcto
        completed = (
            sessions
            .annotate(correctos=Count('attempts', filter=Q(attempts__is_correct=True)))
            .filter(correctos__gt=0)
            .count()
        )

        if completed == 0:
            return None

        return total_tries / completed

    def get_global_average_of_averages(self, exclude_user=True) -> float | None:
        """
        Calcula la media de los promedios individuales de intentos/partidas completas por usuario.
        Solo cuenta a los users que tengan al menos una partida completa.
        """
        # Buscamos todos los user_id que hayan jugado este juego (EXTRA)
        user_ids = (
            GameAttempt.objects
            .filter(session__game=self.game)
            .exclude(user=self.user if exclude_user else None)
            .values_list('user', flat=True)
            .distinct()
        )

        average = []
        for user_id in user_ids:
            # Seteamos el user actual
            user = User.objects.get(pk=user_id)
            # OJO: si ScoreService necesita user instance, no id
            avg = ScoreService(user, self.game).get_user_average_attempts()
            if avg is not None:
                average.append(avg)
        if not average:
            return None
        return sum(average) / len(average)

    # ---------- Internals ----------
    def _points_for_attempts(self, n: int) -> int:
        # 1) Busca regla específica del juego
        rule = (
            ScoringRule.objects
            .filter(game=self.game, attempt_no=n)
            .first()
            or ScoringRule.objects.filter(game__isnull=True, attempt_no=n).first()
        )
        if rule:
            return rule.points

        # 2) Fallback: 1-3 ya deberían estar en ScoringRule
        dec   = getattr(settings, "SCORING_FALLBACK", {}).get("decrement", 10)
        floor = getattr(settings, "SCORING_FALLBACK", {}).get("floor", 0)
        pts   = 50 - dec * (n - 3)  # n=4 → 40, n=5 → 30…
        return max(floor, pts)

