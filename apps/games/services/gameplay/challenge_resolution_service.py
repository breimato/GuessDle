from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.accounts.services.notification_service import NotificationService
from apps.accounts.models import Challenge
from apps.accounts.services.score_service import ScoreService
from django.db import transaction


class ChallengeResolutionService:

    def __init__(self, challenge, acting_user=None):
        self.challenge = challenge
        self.acting_user = acting_user or challenge.challenger

    def resolve_and_assign_points(self):
        with transaction.atomic():
            challenge = (
                Challenge.objects.select_for_update()
                .select_related("challenger", "opponent", "game", "mode", "winner")
                .get(pk=self.challenge.pk)
            )
            challenge_manager = ChallengeManager(user=self.acting_user, challenge=challenge)
            challenge_manager.calculate_winner()

            if not challenge.completed:
                self.challenge = challenge
                return {"status": "already-resolved"}
            if challenge.stake_settled:
                self.challenge = challenge
                return self._build_status_payload(challenge)

            if challenge.winner is None:
                self._settle_tie(challenge)
            else:
                self._settle_winner(challenge)

            challenge.points_assigned = True
            challenge.stake_settled = True
            challenge.save(update_fields=["points_assigned", "stake_settled"])
            self.challenge = challenge

        NotificationService.notify_challenge_outcome(self.challenge, self.acting_user)
        return self._build_status_payload(self.challenge)

    @staticmethod
    def _settle_tie(challenge):
        stake_points = float(challenge.stake_points or 0)
        for participant in (challenge.challenger, challenge.opponent):
            score_service = ScoreService(participant, challenge.game, mode=challenge.mode)
            score_service.score_obj.elo -= stake_points
            score_service.score_obj.save(update_fields=("elo",))

    @staticmethod
    def _settle_winner(challenge):
        stake_points = float(challenge.stake_points or 0)
        winner = challenge.winner
        loser = (
            challenge.challenger
            if winner == challenge.opponent
            else challenge.opponent
        )

        winner_score = ScoreService(winner, challenge.game, mode=challenge.mode)
        loser_score = ScoreService(loser, challenge.game, mode=challenge.mode)
        winner_score.score_obj.elo += stake_points
        loser_score.score_obj.elo -= stake_points
        winner_score.score_obj.save(update_fields=("elo",))
        loser_score.score_obj.save(update_fields=("elo",))

    @staticmethod
    def _build_status_payload(challenge):
        stake_points = float(challenge.stake_points or 0)
        if challenge.winner is None:
            return {
                "status": "tie",
                "users": [challenge.challenger, challenge.opponent],
                "stake_points": stake_points,
                "point_deltas": {
                    challenge.challenger.username: -stake_points,
                    challenge.opponent.username: -stake_points,
                },
            }

        winner = challenge.winner
        loser = challenge.challenger if winner == challenge.opponent else challenge.opponent
        return {
            "status": "winner",
            "winner": winner,
            "loser": loser,
            "stake_points": stake_points,
            "point_deltas": {
                winner.username: stake_points,
                loser.username: -stake_points,
            },
        }
