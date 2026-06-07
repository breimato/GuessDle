from django.utils import timezone

from apps.games.models import PlaySession
from apps.games.services.proximity.game_config import TEAM_TIMER_SECONDS
from apps.games.services.proximity.score_service import ProximityScoreService


class ProximityTimeoutService:
    def __init__(self, game, mode, user):
        self.game = game
        self.mode = mode
        self.user = user

    def is_past_deadline(self, session: PlaySession) -> bool:
        if not session.proximity_started_at:
            return False
        elapsed = (timezone.now() - session.proximity_started_at).total_seconds()
        return elapsed > TEAM_TIMER_SECONDS

    def fail_timed_out(self, session: PlaySession) -> dict:
        if session.proximity_completed or session.proximity_timed_out:
            return {"already_finished": True}
        if session.proximity_attempts.exists():
            return {"already_finished": True}

        session.proximity_timed_out = True
        session.proximity_first_distance = None
        session.proximity_score_locked = None
        session.save(
            update_fields=[
                "proximity_timed_out",
                "proximity_first_distance",
                "proximity_score_locked",
            ]
        )
        points = ProximityScoreService(self.user, self.game, self.mode).apply_completion(session)
        return {"timed_out": True, "points_awarded": points, "score_locked": None}
