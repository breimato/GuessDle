from apps.games.models import PlaySession, PlaySessionType


class PlaySessionService:
    @staticmethod
    def _resolve_mode(*, daily_target=None, extra_play=None, challenge=None):
        if daily_target:
            return daily_target.mode
        if extra_play:
            return extra_play.mode
        if challenge:
            return challenge.mode
        return None

    @staticmethod
    def get_or_create(user, game, *, daily_target=None, extra_play=None, challenge=None):
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

        mode = PlaySessionService._resolve_mode(
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        play_session, created = PlaySession.objects.get_or_create(
            user=user,
            game=game,
            session_type=session_type,
            reference_id=reference_id,
            defaults={"mode": mode},
        )
        if not created and play_session.mode_id != (mode.id if mode else None):
            play_session.mode = mode
            play_session.save(update_fields=["mode"])
        return play_session
