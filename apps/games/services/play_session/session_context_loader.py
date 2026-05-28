from apps.games.services.catalog.attempts import build_attempts
from apps.games.services.play_session.play_context import PlayContext
from apps.games.models import GameAttempt
from apps.games.services.play_session.play_session_service import PlaySessionService


class SessionContextLoader:

    def __init__(self, request, game, *, daily_target=None, extra_play=None, challenge=None):
        self.request = request
        self.game = game
        self.play_context = PlayContext.exactly_one(
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

    def load(self):
        session = PlaySessionService.get_or_create_from_context(
            self.request.user,
            self.game,
            self.play_context,
        )
        target_item = self.play_context.target

        attempts_query = GameAttempt.objects.filter(session=session).order_by("-attempted_at")
        attempts = build_attempts(
            self.game,
            [attempt.guess for attempt in attempts_query],
            target_item,
        )

        return session, target_item, attempts_query, attempts
