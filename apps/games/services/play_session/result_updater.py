from apps.games.services.play_session.outcome_registry import resolve_outcome
from apps.games.services.play_session.play_context import PlayContext


class ResultUpdater:

    def __init__(self, game, user):
        self.game = game
        self.user = user

    def update_for_game(self, *, daily_target=None, extra_play=None, challenge=None):
        play_context = PlayContext.exactly_one(
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )
        return resolve_outcome(self.game, self.user, play_context)
