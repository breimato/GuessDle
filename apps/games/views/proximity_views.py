from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.games.models import Game
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.services.proximity.context_builder import ProximityContextBuilder
from apps.games.services.proximity.filter_service import ProximityFilterService
from apps.games.services.proximity.guess_processor import ProximityGuessProcessor
from apps.games.services.proximity.pool_service import ProximityPoolService
from apps.games.services.proximity.session_service import ProximitySessionService
from apps.games.services.proximity.target_service import ProximityTargetService
from apps.games.services.proximity.timeout_service import ProximityTimeoutService


def _filter_payload_from_request(request, game: Game) -> dict:
    from apps.games.services.proximity.game_config import proximity_game_kind

    kind = proximity_game_kind(game)
    if kind == "pokemon":
        return {"generations": request.POST.getlist("generations")}
    if kind == "lol":
        return {"years": request.POST.getlist("years")}
    if kind == "one_piece":
        return {"arcs": request.POST.getlist("arcs"), "media": request.POST.get("media")}
    return {}


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


@never_cache
@login_required
@csrf_protect
def proximity_filters(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_proximity_mode(game, mode_slug)
    filter_service = ProximityFilterService(game)
    target_service = ProximityTargetService(game, request.user, mode)
    assignment = target_service.get_today_assignment()

    if request.method == "POST":
        try:
            config = filter_service.normalize(_filter_payload_from_request(request, game))
        except ValidationError as error:
            messages.error(request, error.message if hasattr(error, "message") else str(error))
            context = ProximityContextBuilder.build_filters_context(request, game, mode)
            return render(request, "games/proximity_filters.html", context)

        if assignment:
            session = ProximitySessionService.get_or_create(
                request.user, game, mode, assignment
            )
            if filter_service.filter_locked(session):
                messages.error(request, "No puedes cambiar los filtros tras haber respondido.")
                return redirect("play_mode", slug=slug, mode_slug=mode_slug)

        pool = ProximityPoolService(game, mode, config)
        if not pool.has_playable_pool():
            messages.error(request, "No hay personajes con esos filtros. Prueba otra combinación.")
            context = ProximityContextBuilder.build_filters_context(request, game, mode)
            return render(request, "games/proximity_filters.html", context)

        if assignment:
            if assignment.filter_config != config:
                assignment.delete()
                assignment = None
            else:
                assignment.filter_config = config
                assignment.save(update_fields=["filter_config"])

        if not assignment:
            assignment = target_service.ensure_assignment(config)
        if not assignment:
            return _render_unavailable(
                request,
                game,
                mode,
                "No se pudo preparar el reto de hoy con esos filtros.",
            )
        return redirect("play_mode", slug=slug, mode_slug=mode_slug)

    if assignment and not ProximityFilterService(game).filter_locked(
        ProximitySessionService.get_or_create(request.user, game, mode, assignment)
    ):
        pass
    elif assignment:
        return redirect("play_mode", slug=slug, mode_slug=mode_slug)

    context = ProximityContextBuilder.build_filters_context(request, game, mode)
    if not ProximityPoolService(game, mode, context["defaults"]).has_playable_pool():
        return _render_unavailable(
            request,
            game,
            mode,
            "Aún no hay contenido disponible para el modo Proximidad.",
        )
    return render(request, "games/proximity_filters.html", context)


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
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_proximity_mode(game, mode_slug)
    assignment = ProximityTargetService(game, request.user, mode).get_today_assignment()
    if not assignment:
        return JsonResponse({"error": "No hay reto de hoy."}, status=400)

    session = ProximitySessionService.get_or_create(
        request.user, game, mode, assignment
    )
    timeout_service = ProximityTimeoutService(game, mode, request.user)
    if not timeout_service.is_past_deadline(session) and not session.proximity_attempts.exists():
        return JsonResponse({"error": "Aún queda tiempo."}, status=400)

    timeout_service.fail_timed_out(session)
    session.refresh_from_db()
    processor = ProximityGuessProcessor(game, mode, request.user)
    payload = processor.build_state(session, assignment)
    return JsonResponse(payload)
