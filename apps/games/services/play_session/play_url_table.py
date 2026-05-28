from django.urls import reverse

from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.play_kind import PlayKind


class PlayUrlTable:

    def __init__(self, game, play_context: PlayContext):
        self.game = game
        self.play_context = play_context

    def surrender_url(self) -> str:
        return self._resolve("surrender")

    def guess_url(self) -> str:
        return self._resolve("guess")

    def reveal_hint_url(self) -> str:
        return self._resolve("reveal_hint")

    def _resolve(self, action: str) -> str:
        builders = _URL_BUILDERS[action]
        return builders[self.play_context.kind](self.game, self.play_context)


def _daily_guess_url(game, play_context: PlayContext) -> str:
    if play_context.mode:
        return reverse("ajax_guess_mode", args=[game.slug, play_context.mode.slug])
    return reverse("ajax_guess", args=[game.slug])


def _daily_surrender_url(game, play_context: PlayContext) -> str:
    if play_context.mode:
        return reverse("ajax_surrender_mode", args=[game.slug, play_context.mode.slug])
    return reverse("ajax_surrender", args=[game.slug])


def _daily_reveal_hint_url(game, play_context: PlayContext) -> str:
    if play_context.mode:
        return reverse("ajax_reveal_hint_mode", args=[game.slug, play_context.mode.slug])
    return reverse("ajax_reveal_hint", args=[game.slug])


_URL_BUILDERS = {
    "guess": {
        PlayKind.EXTRA: lambda game, ctx: reverse("ajax_guess_extra", args=[ctx.extra_play.id]),
        PlayKind.CHALLENGE: lambda game, ctx: reverse(
            "ajax_guess_challenge", args=[ctx.challenge.id]
        ),
        PlayKind.DAILY: _daily_guess_url,
    },
    "surrender": {
        PlayKind.EXTRA: lambda game, ctx: reverse(
            "ajax_surrender_extra", args=[ctx.extra_play.id]
        ),
        PlayKind.CHALLENGE: lambda game, ctx: reverse(
            "ajax_surrender_challenge", args=[ctx.challenge.id]
        ),
        PlayKind.DAILY: _daily_surrender_url,
    },
    "reveal_hint": {
        PlayKind.EXTRA: lambda game, ctx: reverse(
            "ajax_reveal_hint_extra", args=[ctx.extra_play.id]
        ),
        PlayKind.CHALLENGE: lambda game, ctx: reverse(
            "ajax_reveal_hint_challenge", args=[ctx.challenge.id]
        ),
        PlayKind.DAILY: _daily_reveal_hint_url,
    },
}
