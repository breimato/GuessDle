from apps.games.models import Game, GameMode, PlaySessionType
from apps.games.services.proximity.pool_service import ProximityPoolService
from apps.games.services.proximity.target_service import ProximityTargetService
from apps.games.services.proximity.filter_service import ProximityFilterService


class ProximityStatusService:
    def __init__(self, game, user, mode: GameMode):
        self.game = game
        self.user = user
        self.mode = mode
        self.target_service = ProximityTargetService(game, user, mode)

    def pool_available(self) -> bool:
        defaults = ProximityFilterService(self.game).defaults()
        return ProximityPoolService(self.game, self.mode, defaults).has_playable_pool()

    def is_resolved_today(self) -> bool:
        assignment = self.target_service.get_today_assignment()
        if not assignment:
            return False
        from apps.games.models import PlaySession

        session = PlaySession.objects.filter(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.PROXIMITY,
            reference_id=assignment.id,
        ).first()
        if not session:
            return False
        return (
            session.proximity_completed
            or session.proximity_timed_out
            or session.proximity_attempts.exists()
        )
