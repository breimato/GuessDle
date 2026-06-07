from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.games.models import Game, GameMode
from apps.games.services.catalog.play_background import resolve_background_url
from apps.games.services.catalog.play_mode_navigation import next_mode_navigation
from apps.games.services.proximity.filter_service import ProximityFilterService
from apps.games.services.silhouette.guess_processor import SilhouetteGuessProcessor
from apps.games.services.silhouette.session_service import SilhouetteSessionService
from apps.games.services.silhouette.target_service import SilhouetteTargetService


class SilhouetteContextBuilder:
    def __init__(self, request, game: Game, mode: GameMode, assignment):
        self.request = request
        self.game = game
        self.mode = mode
        self.assignment = assignment
        self.user = request.user

    def build(self) -> dict:
        session = SilhouetteSessionService.get_or_create(
            self.user, self.game, self.mode, self.assignment
        )
        processor = SilhouetteGuessProcessor(self.game, self.mode, self.user)
        state = processor.build_state(session, self.assignment)
        target_item = self.assignment.target_item
        image_url = target_item.get_image_url()

        return {
            "game": self.game,
            "game_mode": self.mode,
            "assignment": self.assignment,
            "target": target_item,
            "sprite_url": image_url,
            "anchor": self.assignment.anchor,
            "zoom_level": state["zoom_level"],
            "attempts": state["attempts"],
            "won": state["won"],
            "surrendered": state["surrendered"],
            "can_play": state["can_play"],
            "remaining_names_json": state["remaining_names_json"],
            "background_url": resolve_background_url(self.game, self.mode),
            "back_to_modes_url": reverse("play", args=[self.game.slug]),
            "guess_url": reverse(
                "silhouette_guess", args=[self.game.slug, self.mode.slug]
            ),
            "surrender_url": reverse(
                "silhouette_surrender", args=[self.game.slug, self.mode.slug]
            ),
            "filters_url": reverse(
                "silhouette_filters", args=[self.game.slug, self.mode.slug]
            ),
            "filters_locked": SilhouetteSessionService.filter_locked(session),
            **next_mode_navigation(self.game, self.user, self.mode),
        }

    @staticmethod
    def build_filters_context(request, game: Game, mode: GameMode) -> dict:
        filter_service = ProximityFilterService(game)
        target_service = SilhouetteTargetService(game, request.user, mode)
        assignment = target_service.get_today_assignment()
        defaults = filter_service.defaults()
        saved_filters = defaults
        if assignment and assignment.filter_config:
            try:
                saved_filters = filter_service.normalize(assignment.filter_config)
            except ValidationError:
                saved_filters = defaults

        filters_locked = False
        if assignment:
            session = SilhouetteSessionService.get_or_create(
                request.user, game, mode, assignment
            )
            filters_locked = SilhouetteSessionService.filter_locked(session)

        return {
            "game": game,
            "game_mode": mode,
            "defaults": defaults,
            "saved_filters": saved_filters,
            "arc_choices": filter_service.arc_choices(),
            "year_choices": filter_service.available_years(),
            "generations": list(range(1, 10)),
            "background_url": resolve_background_url(game, mode),
            "back_to_modes_url": reverse("play", args=[game.slug]),
            "play_url": reverse("play_mode", args=[game.slug, mode.slug]),
            "filters_locked": filters_locked,
        }
