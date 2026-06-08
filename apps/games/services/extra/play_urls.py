from django.urls import reverse

from apps.games.models import Game, GameMode


def resolve_start_extra_url(game: Game, mode: GameMode | None) -> str:
    if mode:
        return reverse("start_extra_daily_mode", args=[game.slug, mode.slug])
    return reverse("start_extra_daily", args=[game.slug])
