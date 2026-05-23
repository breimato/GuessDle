"""Service to retrieve or initialize a PlaySession for a user and game."""

from apps.games.models import PlaySession, PlaySessionType


class PlaySessionService:
    """Manages the creation and retrieval of play sessions for different modes (Daily, Extra, Challenge)."""

    @staticmethod
    def get_or_create(user, game, *, daily_target=None, extra_play=None, challenge=None):
        """Retrieve an existing play session or create a new one for the given parameters."""

        if sum(bool(param) for param in (daily_target, extra_play, challenge)) != 1:
            raise ValueError("Must specify exactly one context (daily_target, extra_play, or challenge).")

        if daily_target:
            session_type = PlaySessionType.DAILY
            reference_id = daily_target.id
        elif extra_play:
            session_type = PlaySessionType.EXTRA
            reference_id = extra_play.id
        else:
            session_type = PlaySessionType.CHALLENGE
            reference_id = challenge.id

        play_session, _ = PlaySession.objects.get_or_create(
            user=user,
            game=game,
            session_type=session_type,
            reference_id=reference_id,
        )
        return play_session
