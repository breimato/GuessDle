"""Helper class to handle request-based views operations for challenge management."""

from django.contrib import messages
from django.contrib.auth.models import User
from django.db import transaction
from django.shortcuts import get_object_or_404

from apps.accounts.models import Challenge, GameElo
from apps.accounts.services.notification_service import NotificationService
from apps.games.models import Game
from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.challenge_stake_service import ChallengeStakeService
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
        if self.challenge.accepted:
            return True, None
        if self.challenge.opponent != self.user:
            return False, "Solo el usuario retado puede aceptar este reto."

        with transaction.atomic():
            challenge = (
                Challenge.objects.select_for_update()
                .select_related("challenger", "opponent", "game", "mode")
                .get(pk=self.challenge.pk)
            )

            if challenge.accepted:
                self.challenge = challenge
                return True, None

            self._lock_score_rows(challenge)
            stake_service = ChallengeStakeService(challenge.game, mode=challenge.mode)
            stake_points = float(challenge.stake_points or 0)

            if not stake_service.can_lock_stake(challenge.challenger, stake_points):
                return False, "El retador ya no tiene puntos disponibles suficientes para esta apuesta."
            if not stake_service.can_lock_stake(challenge.opponent, stake_points):
                return False, "Ya no tienes puntos disponibles suficientes para esta apuesta."

            challenge.accepted = True
            challenge.save(update_fields=["accepted"])
            self.challenge = challenge

        NotificationService.notify_challenge_accepted(self.challenge)
        return True, None

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
        raw_stake_points = request.POST.get("stake_points", "").strip()

        if not opponent_id or not game_id:
            return None, "Faltan parámetros."
        if not raw_stake_points:
            return None, "Debes indicar los puntos de la apuesta."

        try:
            opponent = get_object_or_404(User, pk=opponent_id)
            game = get_object_or_404(Game, pk=game_id)
        except Exception:
            return None, "Opponent or game does not exist"

        try:
            stake_points = float(raw_stake_points)
        except ValueError:
            return None, "Los puntos apostados deben ser un número válido."
        if stake_points <= 0:
            return None, "Los puntos apostados deben ser mayores que cero."
        if opponent == request.user:
            return None, "No puedes retarte a ti mismo."

        resolver = ModeResolver(game)
        mode = resolver.resolve(mode_slug) if mode_slug else None
        if resolver.has_modes() and not mode:
            return None, "Debes elegir una dificultad."

        stake_service = ChallengeStakeService(game, mode=mode)
        max_stake = stake_service.max_stake_between(request.user, opponent)
        if stake_points > max_stake:
            return None, (
                f"No se puede retar con esa cantidad. El máximo permitido para este reto es {int(max_stake)} puntos."
            )

        with transaction.atomic():
            target = TargetService(game, request.user, mode=mode).get_random_item()
            challenge = Challenge.objects.create(
                challenger=request.user,
                opponent=opponent,
                game=game,
                mode=mode,
                target=target,
                stake_points=stake_points,
            )
            NotificationService.notify_challenge_received(challenge)

        return challenge, None

    @staticmethod
    def _lock_score_rows(challenge):
        players = [challenge.challenger, challenge.opponent]
        queryset = GameElo.objects.select_for_update().filter(game=challenge.game, user__in=players)
        if challenge.mode_id is None:
            queryset = queryset.filter(mode__isnull=True)
        else:
            queryset = queryset.filter(mode=challenge.mode)
        list(queryset)

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

        NotificationService.notify_challenge_cancelled(challenge)
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

        NotificationService.notify_challenge_rejected(challenge)
        challenge.delete()
        return True
