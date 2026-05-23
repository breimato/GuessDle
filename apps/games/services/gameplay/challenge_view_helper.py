"""Helper class to handle request-based views operations for challenge management."""

from django.contrib import messages
from apps.games.services.gameplay.challenger_manager import ChallengeManager


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
