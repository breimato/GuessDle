from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.accounts.models import Challenge
from apps.games.models import GameAttempt, Game
from apps.accounts.services.score_service import ScoreService
from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.games.services.gameplay.target_service import TargetService


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


    @staticmethod
    def create_challenge(request):
        if request.method != "POST":
            return None, "Invalid method"

        opponent_id = request.POST.get("opponent")
        game_id = request.POST.get("game")

        if not opponent_id or not game_id:
            return None, "Missing parameters"

        try:
            opponent = get_object_or_404(User, pk=opponent_id)
            game = get_object_or_404(Game, pk=game_id)
        except Exception:
            return None, "Opponent or game does not exist"

        with transaction.atomic():
            target = TargetService(game, request.user).get_random_item()
            challenge = Challenge.objects.create(
                challenger=request.user,
                opponent=opponent,
                game=game,
                target=target
            )

        return challenge, None

    @staticmethod
    def cancel_challenge(request, challenge_id):
        challenge = Challenge.objects.filter(
            id=challenge_id,
            challenger=request.user,
            accepted=False,
            completed=False
        ).first()
        if not challenge:
            return False
        challenge.delete()
        return True

    @staticmethod
    def reject_challenge(request, challenge_id):
        challenge = Challenge.objects.filter(
            id=challenge_id,
            opponent=request.user,
            accepted=False,
            completed=False
        ).first()
        if not challenge:
            return False
        challenge.delete()
        return True
