from django.contrib import messages
from apps.games.models import GameAttempt
from apps.accounts.services.score_service import ScoreService
from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.play_session_service import PlaySessionService

class ChallengeViewHelper:
    """
    Métodos que necesitan request (por ejemplo, leer POST, mostrar messages).
    Internamente delega la lógica de “quién ganó” a ChallengeManager.
    """
    def __init__(self, request, challenge):
        self.request = request
        self.user = request.user
        self.challenge = challenge
        self.domain = ChallengeManager(user=self.user, challenge=challenge)

    def accept_if_needed(self):
        """
        Si soy el opponent y aún no acepté, lo marco.
        (Esto no devuelve nada, solo persiste en DB).
        """
        if not self.challenge.accepted and self.challenge.opponent == self.user:
            self.challenge.accepted = True
            self.challenge.save(update_fields=["accepted"])

    def ensure_participant(self):
        """
        Verifica que request.user sea challenger u opponent.
        """
        return self.user in (self.challenge.challenger, self.challenge.opponent)

    def assign_attempts_from_post(self):
        """
        Lee el número de intentos desde POST y lo guarda en el campo
        adecuado de Challenge (challenger_attempts u opponent_attempts).
        Devuelve True si OK, False si hubo error (y enseña message).
        """
        try:
            attempts = int(self.request.POST.get("attempts"))
        except (TypeError, ValueError):
            messages.error(self.request, "Número de intentos inválido.")
            return False

        if self.user == self.challenge.challenger:
            self.challenge.challenger_attempts = attempts
        else:
            self.challenge.opponent_attempts = attempts

        self.challenge.save(update_fields=["challenger_attempts", "opponent_attempts"])
        return True

    def resolve_if_ready(self):
        ca = self.challenge.challenger_attempts
        oa = self.challenge.opponent_attempts
        if ca is not None and oa is not None and not self.challenge.completed:
            # Esto marca winner y completed, pero NO toca ScoreService
            self.domain.calculate_winner()
            # Ya no asignas puntos aquí

