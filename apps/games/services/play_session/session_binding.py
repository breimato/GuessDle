from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.play_kind import PlayKind
from apps.games.models import PlaySessionType


def resolve_session_binding(play_context: PlayContext) -> tuple[str, int]:
    bindings = {
        PlayKind.DAILY: lambda: (
            PlaySessionType.DAILY,
            play_context.daily_target.id,
        ),
        PlayKind.EXTRA: lambda: (
            PlaySessionType.EXTRA,
            play_context.extra_play.id,
        ),
        PlayKind.CHALLENGE: lambda: (
            PlaySessionType.CHALLENGE,
            play_context.challenge.id,
        ),
    }
    return bindings[play_context.kind]()
