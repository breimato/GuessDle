from dataclasses import dataclass
from typing import Callable, Protocol

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render

from apps.games.models import Game, GameMode
from apps.games.services.proximity.context_builder import ProximityContextBuilder
from apps.games.services.proximity.filter_service import ProximityFilterService


class FilterTargetService(Protocol):
    def get_today_assignment(self): ...

    def ensure_assignment(self, filter_config: dict): ...


class FilterPoolService(Protocol):
    def __init__(self, game: Game, mode: GameMode, filter_config: dict): ...

    def has_playable_pool(self) -> bool: ...


class FilterSessionService(Protocol):
    @staticmethod
    def get_or_create(user, game: Game, mode: GameMode, assignment): ...

    @staticmethod
    def filter_locked(session) -> bool: ...


@dataclass(frozen=True)
class FilteredModeFiltersConfig:
    game: Game
    mode: GameMode
    target_service_factory: Callable[[Game, object, GameMode], FilterTargetService]
    pool_service_factory: Callable[[Game, GameMode, dict], FilterPoolService]
    session_service: FilterSessionService
    filters_url_name: str
    play_url_name: str = "play_mode"
    unavailable_message: str = "Aún no hay contenido disponible para este modo."
    empty_pool_message: str = "No hay personajes con esos filtros. Prueba otra combinación."
    filters_locked_message: str = "No puedes cambiar los filtros tras haber respondido."
    assignment_error_message: str = "No se pudo preparar el reto de hoy con esos filtros."


def build_filter_payload(request: HttpRequest, game: Game) -> dict:
    if game.slug == "pokemon" or game.slug.startswith("pokemon"):
        return {"generations": request.POST.getlist("generations")}
    if game.slug in ("league-of-legends", "lol") or game.slug.startswith("lol"):
        return {"years": request.POST.getlist("years")}
    if game.slug == "one-piece" or game.slug.startswith("one-piece"):
        return {
            "arcs": request.POST.getlist("arcs"),
            "media": request.POST.get("media"),
        }
    return {}


def handle_filtered_mode_filters(
    request: HttpRequest,
    config: FilteredModeFiltersConfig,
) -> HttpResponse:
    filter_service = ProximityFilterService(config.game)
    target_service = config.target_service_factory(
        config.game, request.user, config.mode
    )
    assignment = target_service.get_today_assignment()

    if request.method == "POST":
        try:
            filter_config = filter_service.normalize(
                build_filter_payload(request, config.game)
            )
        except ValidationError as error:
            messages.error(
                request,
                error.message if hasattr(error, "message") else str(error),
            )
            context = _build_filters_context(request, config, filter_service, target_service)
            return render(request, "games/proximity_filters.html", context)

        if assignment:
            session = config.session_service.get_or_create(
                request.user, config.game, config.mode, assignment
            )
            if config.session_service.filter_locked(session):
                messages.error(request, config.filters_locked_message)
                return redirect(config.play_url_name, slug=config.game.slug, mode_slug=config.mode.slug)

        pool = config.pool_service_factory(config.game, config.mode, filter_config)
        if not pool.has_playable_pool():
            messages.error(request, config.empty_pool_message)
            context = _build_filters_context(request, config, filter_service, target_service)
            return render(request, "games/proximity_filters.html", context)

        if assignment:
            if assignment.filter_config != filter_config:
                assignment.delete()
                assignment = None
            else:
                assignment.filter_config = filter_config
                assignment.save(update_fields=["filter_config"])

        if not assignment:
            assignment = target_service.ensure_assignment(filter_config)
        if not assignment:
            return render(
                request,
                "games/silhouette_unavailable.html"
                if config.mode.is_silhouette
                else "games/proximity_unavailable.html",
                {
                    "game": config.game,
                    "game_mode": config.mode,
                    "message": config.assignment_error_message,
                    "back_to_modes_url": _back_to_modes_url(config.game),
                },
            )
        return redirect(config.play_url_name, slug=config.game.slug, mode_slug=config.mode.slug)

    if assignment and not config.session_service.filter_locked(
        config.session_service.get_or_create(
            request.user, config.game, config.mode, assignment
        )
    ):
        pass
    elif assignment:
        return redirect(config.play_url_name, slug=config.game.slug, mode_slug=config.mode.slug)

    context = _build_filters_context(request, config, filter_service, target_service)
    defaults = filter_service.defaults()
    default_pool = config.pool_service_factory(config.game, config.mode, defaults)
    if not default_pool.has_playable_pool():
        unavailable_template = (
            "games/silhouette_unavailable.html"
            if config.mode.is_silhouette
            else "games/proximity_unavailable.html"
        )
        return render(
            request,
            unavailable_template,
            {
                "game": config.game,
                "game_mode": config.mode,
                "message": config.unavailable_message,
                "back_to_modes_url": _back_to_modes_url(config.game),
            },
        )
    return render(request, "games/proximity_filters.html", context)


def _back_to_modes_url(game: Game) -> str:
    from django.urls import reverse

    return reverse("play", args=[game.slug])


def _build_filters_context(request, config, filter_service, target_service):
    if config.mode.is_proximity:
        return ProximityContextBuilder.build_filters_context(
            request, config.game, config.mode
        )
    from apps.games.services.silhouette.context_builder import SilhouetteContextBuilder

    return SilhouetteContextBuilder.build_filters_context(
        request, config.game, config.mode
    )
