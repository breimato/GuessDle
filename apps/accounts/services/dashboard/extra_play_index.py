from dataclasses import dataclass, field

from django.urls import reverse

from apps.games.services.extra.extra_daily_service import ExtraDailyService
from apps.games.services.catalog.mode_resolver import ModeResolver


@dataclass
class ExtraPlayIndex:
    active_by_slug: dict = field(default_factory=dict)
    latest_by_slug: dict = field(default_factory=dict)
    active_by_game_mode: dict = field(default_factory=dict)


def build_extra_play_index(today_extras) -> ExtraPlayIndex:
    index = ExtraPlayIndex()

    for extra in today_extras:
        slug = extra.game.slug
        index.latest_by_slug.setdefault(slug, extra.id)

        if extra.completed:
            continue

        index.active_by_slug.setdefault(slug, extra.id)
        if extra.mode_id:
            index.active_by_game_mode[(slug, extra.mode.slug)] = extra.id

    return index


def resolve_game_redirect_url(game, index: ExtraPlayIndex, user) -> str:
    slug = game.slug
    resolver = ModeResolver(game)

    if resolver.has_modes():
        return reverse("play", args=[game.slug])

    if slug in index.active_by_slug:
        return reverse("play_extra_daily", args=[index.active_by_slug[slug]])

    if slug in index.latest_by_slug and ExtraDailyService(user, game).max_reached():
        return reverse("play_extra_daily", args=[index.latest_by_slug[slug]])

    return reverse("play", args=[game.slug])
