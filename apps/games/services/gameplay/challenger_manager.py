"""Domain logic manager for challenges (determining winners, saving completions, checking ties)."""


class ChallengeManager:
    """Manages pure domain decisions about challenges, including resolving outcomes and ties."""

    def __init__(self, *, user, challenge):
        """Initialize challenge manager."""

        self.user = user
        self.challenge = challenge

    def _both_attempts_submitted(self):
        """Determine if both participants have submitted their attempt counts."""

        return (
            self.challenge.challenger_attempts is not None
            and self.challenge.opponent_attempts is not None
        )

    def _winner_user(self):
        """Determine the winning user based on who took fewer attempts. Returns None on tie or missing data."""

        challenger_attempts_count = self.challenge.challenger_attempts
        opponent_attempts_count = self.challenge.opponent_attempts
        if (
            challenger_attempts_count is None
            or opponent_attempts_count is None
            or challenger_attempts_count == opponent_attempts_count
        ):
            return None
        return (
            self.challenge.challenger
            if challenger_attempts_count < opponent_attempts_count
            else self.challenge.opponent
        )

    def calculate_winner(self) -> bool:
        """Calculate the challenge outcome, mark completion, persist results, and return if the current user won."""

        if not self._both_attempts_submitted():
            return False

        winner = self._winner_user()
        if winner is None:
            self.challenge.completed = True
            self.challenge.save(update_fields=["completed"])
            return False

        if self.challenge.winner_id is None:
            self.challenge.winner = winner
            self.challenge.completed = True
            self.challenge.save(update_fields=["winner", "completed"])

        return winner == self.user

    def get_tied_users(self):
        """Return a list containing both participants if they finished with a tie (equal attempts), or an empty list."""

        challenger_attempts_count = self.challenge.challenger_attempts
        opponent_attempts_count = self.challenge.opponent_attempts

        if (
            challenger_attempts_count is not None
            and opponent_attempts_count is not None
            and challenger_attempts_count == opponent_attempts_count
        ):
            return [self.challenge.challenger, self.challenge.opponent]
        return []
