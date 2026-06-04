from django.utils import timezone

from apps.games.models import Game, GameMode, PlaySession, PlaySessionType, ProximityDailyAssignment


class ProximitySessionService:
    @staticmethod
    def get_or_create(
        user,
        game: Game,
        mode: GameMode,
        assignment: ProximityDailyAssignment,
    ) -> PlaySession:
        session, created = PlaySession.objects.get_or_create(
            user=user,
            game=game,
            session_type=PlaySessionType.PROXIMITY,
            reference_id=assignment.id,
            defaults={
                "mode": mode,
                "proximity_filter": assignment.filter_config,
            },
        )
        if not created and session.proximity_filter != assignment.filter_config:
            session.proximity_filter = assignment.filter_config
            session.save(update_fields=["proximity_filter"])
        return session

    @staticmethod
    def ensure_started(session: PlaySession, *, is_team: bool) -> PlaySession:
        if not is_team or session.proximity_started_at:
            return session
        session.proximity_started_at = timezone.now()
        session.save(update_fields=["proximity_started_at"])
        return session

    @staticmethod
    def is_team_user(user) -> bool:
        return bool(getattr(getattr(user, "profile", None), "is_team_account", False))
