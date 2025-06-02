from django.conf import settings
from apps.games.models import ScoringRule, GameAttempt
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
