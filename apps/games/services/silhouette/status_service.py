from apps.games.models import Game, GameMode, PlaySession, PlaySessionType
from apps.games.services.proximity.filter_service import ProximityFilterService
from apps.games.services.silhouette.pool_service import SilhouettePoolService
from apps.games.services.silhouette.target_service import SilhouetteTargetService


class SilhouetteStatusService:
    def __init__(self, game, user, mode: GameMode):
        self.game = game
        self.user = user
        self.mode = mode
        self.target_service = SilhouetteTargetService(game, user, mode)

    def pool_available(self) -> bool:
        defaults = ProximityFilterService(self.game).defaults()
        return SilhouettePoolService(self.game, self.mode, defaults).has_playable_pool()

    def is_resolved_today(self) -> bool:
        assignment = self.target_service.get_today_assignment()
        if not assignment:
            return False

        session = PlaySession.objects.filter(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.SILHOUETTE,
            reference_id=assignment.id,
        ).first()
        if not session:
            return False

        return (
            session.surrendered
            or session.attempts.filter(is_correct=True).exists()
            or session.attempts.exists()
        )
