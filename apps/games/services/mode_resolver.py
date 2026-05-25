from django.shortcuts import get_object_or_404

from apps.games.models import Game, GameMode


class ModeResolver:
    def __init__(self, game: Game):
        self.game = game

    def active_modes(self):
        return self.game.modes.filter(active=True).order_by("sort_order", "slug")

    def has_modes(self) -> bool:
        return self.active_modes().exists()

    def resolve(self, mode_slug: str | None) -> GameMode | None:
        if not self.has_modes():
            return None
        if not mode_slug:
            return None
        return get_object_or_404(GameMode, game=self.game, slug=mode_slug, active=True)

    def default_mode(self) -> GameMode | None:
        return self.active_modes().first()
