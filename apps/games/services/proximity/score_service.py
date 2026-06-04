from apps.accounts.services.wallet.score_service import ScoreService
from apps.games.models import Game, GameMode, PlaySession


class ProximityScoreService:
    def __init__(self, user, game: Game, mode: GameMode):
        self.user = user
        self.game = game
        self.mode = mode

    @staticmethod
    def points_for_distance(distance: int | None) -> int:
        if distance is None:
            return 0
        return int(distance)

    def apply_completion(self, session: PlaySession) -> int:
        if session.proximity_completed:
            return session.proximity_score_locked or 0
        points = session.proximity_score_locked
        if points is None:
            points = self.points_for_distance(session.proximity_first_distance)
        session.proximity_completed = True
        session.save(update_fields=["proximity_completed"])
        wallet = ScoreService(self.user, self.game, mode=self.mode)
        wallet.score_obj.elo += points
        wallet.score_obj.partidas += 1
        wallet.score_obj.save(update_fields=("elo", "partidas"))
        return points
