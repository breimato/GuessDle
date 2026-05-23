"""Service to manage and orchestrate the resolution and point assignments for a challenge between two players."""

from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.result_updater import ResultUpdater
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.accounts.services.score_service import ScoreService
from apps.games.models import GameAttempt


class ChallengeResolutionService:
    """Orchestrates challenge resolution: determines winner/tie, updates game scores, and marks challenge complete."""

    def __init__(self, challenge, acting_user=None):
        """Initialize challenge resolution service."""

        self.challenge = challenge
        self.acting_user = acting_user or challenge.challenger

    def resolve_and_assign_points(self):
        """Calculate the winner/tie for the challenge, assign base/bonus points, and finalize the challenge status."""

        challenge_manager = ChallengeManager(user=self.acting_user, challenge=self.challenge)
        challenge_manager.calculate_winner()

        if not self.challenge.completed or self.challenge.points_assigned:
            return {"status": "already-resolved"}

        if self.challenge.winner is None:
            ResultUpdater(self.challenge.game, self.acting_user).update_for_game(challenge=self.challenge)
            self.challenge.points_assigned = True
            self.challenge.save(update_fields=["points_assigned"])
            return {
                "status": "tie",
                "users": challenge_manager.get_tied_users(),
            }

        winner = self.challenge.winner
        loser = self.challenge.challenger if winner == self.challenge.opponent else self.challenge.opponent

        loser_play_session = PlaySessionService.get_or_create(
            loser,
            self.challenge.game,
            challenge=self.challenge
        )
        loser_attempts_count = GameAttempt.objects.filter(session=loser_play_session).count()
        loser_score_service = ScoreService(loser, self.challenge.game)
        loser_score_service.add_points_for_attempts(loser_attempts_count)

        ResultUpdater(self.challenge.game, winner).update_for_game(challenge=self.challenge)

        self.challenge.points_assigned = True
        self.challenge.save(update_fields=["points_assigned"])

        return {
            "status": "winner",
            "winner": winner,
            "loser": loser,
        }
