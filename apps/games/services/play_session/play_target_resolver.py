from apps.games.services.play_session.play_context import PlayContext


def resolve_play_target(*, daily_target=None, extra_play=None, challenge=None):
    return PlayContext.exactly_one(
        daily_target=daily_target,
        extra_play=extra_play,
        challenge=challenge,
    ).target
