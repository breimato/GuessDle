from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.games.models import Game
from apps.games.services.catalog.filtered_mode_filters import (
    FilteredModeFiltersConfig,
    handle_filtered_mode_filters,
)
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.services.proximity.pool_service import ProximityPoolService
from apps.games.services.proximity.session_service import ProximitySessionService
from apps.games.services.proximity.target_service import ProximityTargetService
from apps.games.services.silhouette.context_builder import SilhouetteContextBuilder
from apps.games.services.silhouette.guess_processor import SilhouetteGuessProcessor
from apps.games.services.silhouette.pool_service import SilhouettePoolService
from apps.games.services.silhouette.session_service import SilhouetteSessionService
from apps.games.services.silhouette.target_service import SilhouetteTargetService


def _resolve_silhouette_mode(game: Game, mode_slug: str):
    mode = ModeResolver(game).resolve(mode_slug)
    if not mode.is_silhouette:
        raise Http404("Este modo no es de tipo silueta.")
    return mode


def _render_unavailable(request, game: Game, mode, message: str):
    return render(
        request,
        "games/silhouette_unavailable.html",
        {
            "game": game,
            "game_mode": mode,
            "message": message,
            "back_to_modes_url": reverse("play", args=[game.slug]),
        },
    )


def _filters_config(game: Game, mode) -> FilteredModeFiltersConfig:
    return FilteredModeFiltersConfig(
        game=game,
        mode=mode,
        target_service_factory=SilhouetteTargetService,
        pool_service_factory=SilhouettePoolService,
        session_service=SilhouetteSessionService,
        filters_url_name="silhouette_filters",
        unavailable_message="Aún no hay Pokémon con imagen disponible para el modo Silueta.",
        empty_pool_message="No hay Pokémon con imagen para esos filtros. Prueba otra combinación.",
        assignment_error_message="No se pudo preparar el reto de hoy con esos filtros.",
    )


@never_cache
@login_required
@csrf_protect
def silhouette_filters(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_silhouette_mode(game, mode_slug)
    return handle_filtered_mode_filters(request, _filters_config(game, mode))


@never_cache
@login_required
@csrf_protect
def play_silhouette_game(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_silhouette_mode(game, mode_slug)
    target_service = SilhouetteTargetService(game, request.user, mode)
    assignment = target_service.get_today_assignment()

    if not assignment:
        return redirect("silhouette_filters", slug=slug, mode_slug=mode_slug)

    if not assignment.target_item.get_image_url():
        return _render_unavailable(
            request,
            game,
            mode,
            "El Pokémon de hoy no tiene imagen disponible.",
        )

    context = SilhouetteContextBuilder(request, game, mode, assignment).build()
    return render(request, "games/play_silhouette.html", context)


@require_POST
@login_required
@never_cache
@csrf_protect
def silhouette_guess(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_silhouette_mode(game, mode_slug)
    assignment = SilhouetteTargetService(game, request.user, mode).get_today_assignment()
    if not assignment:
        return JsonResponse({"error": "No hay reto de hoy."}, status=400)

    processor = SilhouetteGuessProcessor(game, mode, request.user)
    is_valid, payload = processor.process(request, assignment)
    if not is_valid:
        return JsonResponse(payload, status=400)
    return JsonResponse(payload)


@require_POST
@login_required
@never_cache
@csrf_protect
def silhouette_surrender(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_silhouette_mode(game, mode_slug)
    assignment = SilhouetteTargetService(game, request.user, mode).get_today_assignment()
    if not assignment:
        return JsonResponse({"error": "No hay reto de hoy."}, status=400)

    processor = SilhouetteGuessProcessor(game, mode, request.user)
    try:
        payload = processor.surrender(assignment)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)
    return JsonResponse(payload)
