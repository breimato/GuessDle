from apps.accounts.services.notification_service import NotificationService
from apps.games.models import GameAttempt
from apps.games.services.gameplay.challenge_resolution_service import ChallengeResolutionService


class ChallengeSurrenderHandler:
    def __init__(self, user):
        self.user = user

    def apply(self, play_session, challenge):
        self._record_attempt_count(play_session, challenge)
        self._notify_rival_if_needed(challenge)
        ChallengeResolutionService(challenge, acting_user=self.user).resolve_and_assign_points()
        challenge.refresh_from_db()
        return self._build_challenge_payload(challenge)

    def _record_attempt_count(self, play_session, challenge):
        attempts_count = GameAttempt.objects.filter(session=play_session).count()
        update_fields = []

        is_challenger = self.user == challenge.challenger
        if is_challenger and challenge.challenger_attempts is None:
            challenge.challenger_attempts = attempts_count
            update_fields.append("challenger_attempts")

        is_opponent = self.user == challenge.opponent
        if is_opponent and challenge.opponent_attempts is None:
            challenge.opponent_attempts = attempts_count
            update_fields.append("opponent_attempts")

        if not update_fields:
            return

        challenge.save(update_fields=update_fields)

    def _notify_rival_if_needed(self, challenge):
        if challenge.completed:
            return

        NotificationService.notify_rival_finished(challenge, self.user)

    def _build_challenge_payload(self, challenge):
        winner_username = challenge.winner.username if challenge.winner else None
        return {
            "completed": challenge.completed,
            "winner": winner_username,
            "challenger": challenge.challenger.username,
            "opponent": challenge.opponent.username,
            "current_user": self.user.username,
            "challenger_attempts": challenge.challenger_attempts,
            "opponent_attempts": challenge.opponent_attempts,
        }
