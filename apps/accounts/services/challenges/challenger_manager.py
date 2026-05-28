"""Domain logic manager for challenges (determining winners, saving completions, checking ties)."""

from apps.games.models import GameAttempt, PlaySession, PlaySessionType


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

    @staticmethod
    def _user_solved(challenge, user) -> bool:
        session = PlaySession.objects.filter(
            user=user,
            game=challenge.game,
            session_type=PlaySessionType.CHALLENGE,
            reference_id=challenge.id,
        ).first()
        if not session:
            return False
        return GameAttempt.objects.filter(session=session, is_correct=True).exists()

    def _sync_attempt_counts_from_sessions(self):
        update_fields = []
        for user, field_name in (
            (self.challenge.challenger, "challenger_attempts"),
            (self.challenge.opponent, "opponent_attempts"),
        ):
            if getattr(self.challenge, field_name) is not None:
                continue
            session = PlaySession.objects.filter(
                user=user,
                game=self.challenge.game,
                session_type=PlaySessionType.CHALLENGE,
                reference_id=self.challenge.id,
            ).first()
            if not session:
                continue
            attempts_count = GameAttempt.objects.filter(session=session).count()
            if attempts_count:
                setattr(self.challenge, field_name, attempts_count)
                update_fields.append(field_name)
        if update_fields:
            self.challenge.save(update_fields=update_fields)

    def _winner_user(self):
        """Determine winner: solved beats unsolved; then fewer attempts; equal unsolved attempts is a tie."""

        challenger_attempts_count = self.challenge.challenger_attempts
        opponent_attempts_count = self.challenge.opponent_attempts
        if challenger_attempts_count is None or opponent_attempts_count is None:
            return None

        challenger_solved = self._user_solved(self.challenge, self.challenge.challenger)
        opponent_solved = self._user_solved(self.challenge, self.challenge.opponent)

        if challenger_solved and not opponent_solved:
            return self.challenge.challenger
        if opponent_solved and not challenger_solved:
            return self.challenge.opponent
        if challenger_solved and opponent_solved:
            if challenger_attempts_count == opponent_attempts_count:
                return None
            return (
                self.challenge.challenger
                if challenger_attempts_count < opponent_attempts_count
                else self.challenge.opponent
            )

        if challenger_attempts_count == opponent_attempts_count:
            return None
        return (
            self.challenge.challenger
            if challenger_attempts_count < opponent_attempts_count
            else self.challenge.opponent
        )

    def calculate_winner(self) -> bool:
        """Calculate the challenge outcome, mark completion, persist results, and return if the current user won."""

        self._sync_attempt_counts_from_sessions()

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
