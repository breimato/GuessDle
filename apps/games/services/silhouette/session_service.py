from apps.games.models import Game, GameMode, PlaySession, PlaySessionType, SilhouetteDailyAssignment


class SilhouetteSessionService:
    @staticmethod
    def get_or_create(
        user,
        game: Game,
        mode: GameMode,
        assignment: SilhouetteDailyAssignment,
    ) -> PlaySession:
        session, created = PlaySession.objects.get_or_create(
            user=user,
            game=game,
            session_type=PlaySessionType.SILHOUETTE,
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
    def filter_locked(session: PlaySession) -> bool:
        return (
            session.surrendered
            or session.attempts.filter(is_correct=True).exists()
            or session.attempts.exists()
        )

    @staticmethod
    def is_team_user(user) -> bool:
        return bool(getattr(getattr(user, "profile", None), "is_team_account", False))
