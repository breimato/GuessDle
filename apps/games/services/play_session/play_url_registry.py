from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.play_url_table import PlayUrlTable


class PlayUrlRegistry:

    def __init__(self, game, *, daily_target=None, extra_play=None, challenge=None, mode=None):
        self._table = PlayUrlTable(
            game,
            PlayContext.exactly_one(
                daily_target=daily_target,
                extra_play=extra_play,
                challenge=challenge,
            ),
        )

    def surrender_url(self) -> str:
        return self._table.surrender_url()

    def guess_url(self) -> str:
        return self._table.guess_url()

    def reveal_hint_url(self) -> str:
        return self._table.reveal_hint_url()
