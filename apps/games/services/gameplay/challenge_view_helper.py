"""Helper class to handle request-based views operations for challenge management."""

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.accounts.models import Challenge
from apps.games.models import Game
from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.target_service import TargetService
from apps.games.services.mode_resolver import ModeResolver


class ChallengeViewHelper:
    """Manages request-based HTTP operations, including checking parameters, acceptance, and attempts updating."""

    def __init__(self, request, challenge):
        """Initialize challenge view helper."""

        self.request = request
        self.user = request.user
        self.challenge = challenge
        self.challenge_manager = ChallengeManager(user=self.user, challenge=challenge)

    def accept_if_needed(self):
        """Accept the challenge automatically if the current user is the opponent and has not accepted yet."""

        if not self.challenge.accepted and self.challenge.opponent == self.user:
            self.challenge.accepted = True
            self.challenge.save(update_fields=["accepted"])

    def ensure_participant(self):
        """Verify if the current user is a valid participant (challenger or opponent) in the challenge."""

        return self.user in (self.challenge.challenger, self.challenge.opponent)

    def assign_attempts_from_post(self):
        """Read attempt count from the request POST and assign it to the user's slot in the challenge model."""

        try:
            attempts_count = int(self.request.POST.get("attempts"))
        except (TypeError, ValueError):
            messages.error(self.request, "Invalid number of attempts.")
            return False

        if self.user == self.challenge.challenger:
            self.challenge.challenger_attempts = attempts_count
        else:
            self.challenge.opponent_attempts = attempts_count

        self.challenge.save(update_fields=["challenger_attempts", "opponent_attempts"])
        return True

    def resolve_if_ready(self):
        """Trigger challenge winner calculation if both participants have submitted their attempt counts."""

        challenger_attempts_count = self.challenge.challenger_attempts
        opponent_attempts_count = self.challenge.opponent_attempts
        if (
            challenger_attempts_count is not None
            and opponent_attempts_count is not None
            and not self.challenge.completed
        ):
            self.challenge_manager.calculate_winner()

    @staticmethod
    def create_challenge(request):
        """Parse POST parameters and create a new pending challenge with a random target item."""

        if request.method != "POST":
            return None, "Invalid method"

        opponent_id = request.POST.get("opponent")
        game_id = request.POST.get("game")
        mode_slug = request.POST.get("mode", "").strip() or None

        if not opponent_id or not game_id:
            return None, "Missing parameters"

        try:
            opponent = get_object_or_404(User, pk=opponent_id)
            game = get_object_or_404(Game, pk=game_id)
        except Exception:
            return None, "Opponent or game does not exist"

        resolver = ModeResolver(game)
        mode = resolver.resolve(mode_slug) if mode_slug else None
        if resolver.has_modes() and not mode:
            return None, "Debes elegir una dificultad."

        with transaction.atomic():
            target = TargetService(game, request.user, mode=mode).get_random_item()
            challenge = Challenge.objects.create(
                challenger=request.user,
                opponent=opponent,
                game=game,
                mode=mode,
                target=target,
            )

        return challenge, None

    @staticmethod
    def cancel_challenge(request, challenge_id):
        """Cancel a pending challenge created by the current user."""

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
        """Reject a pending challenge received by the current user."""

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
