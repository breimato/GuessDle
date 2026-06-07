from django.contrib.auth.decorators import login_required
from django.http import Http404
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
from apps.games.services.proximity.context_builder import ProximityContextBuilder
from apps.games.services.proximity.guess_processor import ProximityGuessProcessor
from apps.games.services.proximity.pool_service import ProximityPoolService
from apps.games.services.proximity.session_service import ProximitySessionService
from apps.games.services.proximity.target_service import ProximityTargetService


def _resolve_proximity_mode(game: Game, mode_slug: str):
    mode = ModeResolver(game).resolve(mode_slug)
    if not mode.is_proximity:
        raise Http404("Este modo no es de tipo proximidad.")
    return mode


def _render_unavailable(request, game: Game, mode, message: str):
    return render(
        request,
        "games/proximity_unavailable.html",
        {
            "game": game,
            "game_mode": mode,
            "message": message,
            "back_to_modes_url": reverse("play", args=[game.slug]),
        },
    )


class _ProximityFilterSessionAdapter:
    @staticmethod
    def get_or_create(user, game, mode, assignment):
        return ProximitySessionService.get_or_create(user, game, mode, assignment)

    @staticmethod
    def filter_locked(session) -> bool:
        from apps.games.services.proximity.filter_service import ProximityFilterService

        return ProximityFilterService(session.game).filter_locked(session)


def _proximity_filters_config(game: Game, mode) -> FilteredModeFiltersConfig:
    return FilteredModeFiltersConfig(
        game=game,
        mode=mode,
        target_service_factory=ProximityTargetService,
        pool_service_factory=ProximityPoolService,
        session_service=_ProximityFilterSessionAdapter,
        filters_url_name="proximity_filters",
        unavailable_message="Aún no hay contenido disponible para el modo Proximidad.",
    )


@never_cache
@login_required
@csrf_protect
def proximity_filters(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_proximity_mode(game, mode_slug)
    return handle_filtered_mode_filters(request, _proximity_filters_config(game, mode))


@never_cache
@login_required
@csrf_protect
def play_proximity_game(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_proximity_mode(game, mode_slug)
    target_service = ProximityTargetService(game, request.user, mode)
    assignment = target_service.get_today_assignment()

    if not assignment:
        return redirect("proximity_filters", slug=slug, mode_slug=mode_slug)

    context = ProximityContextBuilder(request, game, mode, assignment).build()
    return render(request, "games/play_proximity.html", context)


@require_POST
@login_required
@never_cache
@csrf_protect
def proximity_guess(request, slug: str, mode_slug: str):
    from django.http import JsonResponse

    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_proximity_mode(game, mode_slug)
    assignment = ProximityTargetService(game, request.user, mode).get_today_assignment()
    if not assignment:
        return JsonResponse({"error": "No hay reto de hoy."}, status=400)

    processor = ProximityGuessProcessor(game, mode, request.user)
    is_valid, payload = processor.process(request, assignment)
    if not is_valid:
        return JsonResponse(payload, status=400)
    return JsonResponse(payload)


@require_POST
@login_required
@never_cache
@csrf_protect
def proximity_timeout(request, slug: str, mode_slug: str):
    from django.http import JsonResponse

    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_proximity_mode(game, mode_slug)
    assignment = ProximityTargetService(game, request.user, mode).get_today_assignment()
    if not assignment:
        return JsonResponse({"error": "No hay reto de hoy."}, status=400)

    processor = ProximityGuessProcessor(game, mode, request.user)
    is_valid, payload = processor.process_timeout(request, assignment)
    if not is_valid:
        return JsonResponse(payload, status=400)
    return JsonResponse(payload)
