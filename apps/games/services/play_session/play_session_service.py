from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.session_binding import resolve_session_binding
from apps.games.models import PlaySession


class PlaySessionService:

    @staticmethod
    def get_or_create_from_context(user, game, play_context: PlayContext) -> PlaySession:
        session_type, reference_id = resolve_session_binding(play_context)
        mode = play_context.mode

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

    @staticmethod
    def get_or_create(user, game, *, daily_target=None, extra_play=None, challenge=None) -> PlaySession:
        play_context = PlayContext.exactly_one(
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )
        return PlaySessionService.get_or_create_from_context(user, game, play_context)
