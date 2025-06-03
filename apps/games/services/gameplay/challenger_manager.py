# apps/games/services/gameplay/challenge_manager.py

from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.accounts.services.score_service import ScoreService
from apps.games.models import GameAttempt

class ChallengeManager:
    """
    Lógica de dominio del reto (calcular ganador, marcar completado,
    persistir winner). No sabe nada de HttpRequest ni messages.
    """
    def __init__(self, *, user, challenge):
        self.user = user
        self.challenge = challenge

    def _both_attempts_submitted(self):
        return (
            self.challenge.challenger_attempts is not None
            and self.challenge.opponent_attempts is not None
        )

    def _winner_user(self):
        ca = self.challenge.challenger_attempts
        oa = self.challenge.opponent_attempts
        if ca is None or oa is None or ca == oa:
            return None  # Inf completa o empate
        return self.challenge.challenger if ca < oa else self.challenge.opponent

    def calculate_winner(self) -> bool:
        """
        ⚠ Devuelve True si `self.user` es el ganador. False si pierde,
        empata o aún no se puede decidir.
        Además, marca el challenge como completado y guarda el winner
        (solo la primera vez que se decide).
        """
        if not self._both_attempts_submitted():
            return False

        ganador = self._winner_user()
        if ganador is None:
            # Empate: marco como completado sin winner
            self.challenge.completed = True
            self.challenge.save(update_fields=["completed"])
            return False

        # Solo persisto la primera vez
        if self.challenge.winner_id is None:
            self.challenge.winner = ganador
            self.challenge.completed = True
            self.challenge.save(update_fields=["winner", "completed"])

        return ganador == self.user
