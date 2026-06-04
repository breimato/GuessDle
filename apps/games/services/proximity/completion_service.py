from apps.games.models import Game, GameMode, ProximityDailyAssignment
from apps.games.services.proximity.score_service import ProximityScoreService
from apps.games.services.proximity.session_service import ProximitySessionService


class ProximityCompletionService:
    def __init__(self, game: Game, mode: GameMode, user):
        self.game = game
        self.mode = mode
        self.user = user

    def surrender(self, assignment: ProximityDailyAssignment) -> dict:
        session = ProximitySessionService.get_or_create(
            self.user, self.game, self.mode, assignment
        )
        if session.proximity_completed or session.surrendered:
            raise ValueError("La partida ya ha terminado.")

        session.surrendered = True
        session.save(update_fields=["surrendered"])
        points = ProximityScoreService(self.user, self.game, self.mode).apply_completion(
            session
        )
        return {"points_awarded": points, "best_distance": session.proximity_best_distance}
