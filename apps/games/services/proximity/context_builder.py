from django.core.exceptions import ValidationError
from django.urls import reverse

from apps.games.models import Game, GameMode, ProximityDailyAssignment
from apps.games.services.catalog.play_background import resolve_background_url
from apps.games.services.catalog.play_mode_navigation import next_mode_navigation
from apps.games.services.proximity.filter_service import ProximityFilterService
from apps.games.services.proximity.guess_processor import ProximityGuessProcessor
from apps.games.services.proximity.game_config import (
    TEAM_TIMER_SECONDS,
    proximity_game_kind,
    proximity_info_text,
)
from apps.games.services.proximity.session_service import ProximitySessionService
from apps.games.services.proximity.timeout_service import ProximityTimeoutService


class ProximityContextBuilder:
    def __init__(self, request, game: Game, mode: GameMode, assignment: ProximityDailyAssignment):
        self.request = request
        self.game = game
        self.mode = mode
        self.assignment = assignment
        self.user = request.user
        self.is_team = ProximitySessionService.is_team_user(self.user)

    def build(self) -> dict:
        session = ProximitySessionService.get_or_create(
            self.user, self.game, self.mode, self.assignment
        )
        if self.is_team and not session.proximity_completed and not session.proximity_timed_out:
            ProximitySessionService.ensure_started(session, is_team=True)
            session.refresh_from_db()
            if (
                not session.proximity_attempts.exists()
                and ProximityTimeoutService(self.game, self.mode, self.user).is_past_deadline(session)
            ):
                ProximityTimeoutService(self.game, self.mode, self.user).fail_timed_out(session)
                session.refresh_from_db()

        processor = ProximityGuessProcessor(self.game, self.mode, self.user)
        state = processor.build_state(session, self.assignment)
        filter_service = ProximityFilterService(self.game)
        prompt = self.assignment.proximity_prompt
        item = self.assignment.target_item
        is_event = prompt is not None and item is None
        game_kind = proximity_game_kind(self.game)
        prompt_question = ""
        if game_kind == "pokemon" and item is not None:
            prompt_question = "¿Qué número de Pokédex es?"

        return {
            "game": self.game,
            "game_mode": self.mode,
            "assignment": self.assignment,
            "won": state["won"],
            "can_play": state["can_play"],
            "timed_out": state["timed_out"],
            "attempts": state["attempts"],
            "answer_value": state["answer_value"],
            "score_locked": state["score_locked"],
            "first_guess_value": state["first_guess_value"],
            "value_unit": state["value_unit"],
            "is_team_play": state["is_team_play"],
            "timer_seconds": TEAM_TIMER_SECONDS if state["is_team_play"] else None,
            "deadline_iso": state["deadline_iso"],
            "prompt_title": item.name if item else "",
            "prompt_image_url": item.get_image_url() if item else None,
            "is_event_prompt": is_event,
            "event_prompt_text": prompt.prompt_text if is_event else "",
            "prompt_question": prompt_question,
            "game_info_text": proximity_info_text(self.game),
            "background_url": resolve_background_url(self.game, self.mode),
            "back_to_modes_url": reverse("play", args=[self.game.slug]),
            "guess_url": reverse(
                "proximity_guess", args=[self.game.slug, self.mode.slug]
            ),
            "timeout_url": reverse(
                "proximity_timeout", args=[self.game.slug, self.mode.slug]
            ),
            "filters_url": reverse(
                "proximity_filters", args=[self.game.slug, self.mode.slug]
            ),
            "filters_locked": filter_service.filter_locked(session),
            **next_mode_navigation(self.game, self.user, self.mode),
        }

    @staticmethod
    def build_filters_context(request, game: Game, mode: GameMode) -> dict:
        filter_service = ProximityFilterService(game)
        saved = {}
        from apps.games.services.proximity.target_service import ProximityTargetService

        target_service = ProximityTargetService(game, request.user, mode)
        assignment = target_service.get_today_assignment()
        defaults = filter_service.defaults()
        saved_filters = defaults
        if assignment and assignment.filter_config:
            try:
                saved_filters = filter_service.normalize(assignment.filter_config)
            except ValidationError:
                saved_filters = defaults

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
            "filters_locked": bool(
                assignment
                and filter_service.filter_locked(
                    ProximitySessionService.get_or_create(
                        request.user, game, mode, assignment
                    )
                )
            ),
        }
