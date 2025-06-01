from apps.games.models import PlaySession, PlaySessionType

class PlaySessionService:
    """Orquesta la vida de una sesión de juego (SRP)."""

    @staticmethod
    def get_or_create(user, game, *, daily_target=None,
                      extra_play=None, challenge=None):
        if sum(bool(x) for x in (daily_target, extra_play, challenge)) != 1:
            raise ValueError("Debes indicar exactamente un contexto.")

        if daily_target:
            session_type = PlaySessionType.DAILY
            ref_id = daily_target.id
        elif extra_play:
            session_type = PlaySessionType.EXTRA
            ref_id = extra_play.id
        else:
            session_type = PlaySessionType.CHALLENGE
            ref_id = challenge.id

        session, _ = PlaySession.objects.get_or_create(
            user=user,
            game=game,
            session_type=session_type,
            reference_id=ref_id,
        )
        return session
