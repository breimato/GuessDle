from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.games.models import Game
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.services.rosco.rosco_context_builder import RoscoContextBuilder
from apps.games.services.rosco.rosco_session_state import session_is_playable
from apps.games.services.rosco.rosco_turn_processor import RoscoTurnProcessor
from apps.games.services.rosco.rosco_access import (
    SATURDAY_ONLY_MESSAGE,
    TEAM_ONLY_MESSAGE,
    user_can_play_rosco,
    user_can_see_rosco,
)
from apps.games.services.rosco.weekly_rosco_service import WeeklyRoscoService


def _resolve_rosco_mode(game: Game, mode_slug: str):
    mode = ModeResolver(game).resolve(mode_slug)
    if not mode.is_rosco:
        raise Http404("Este modo no es un rosco Pasapalabra.")
    return mode


def _unavailable_response(game: Game):
    if WeeklyRoscoService.has_question_bank(game):
        return None
    return JsonResponse(
        {"error": "El rosco Pasapalabra aún no está configurado para este juego."},
        status=503,
    )


def _blocked_rosco_access(request, slug: str):
    if user_can_play_rosco(request.user):
        return None
    if not user_can_see_rosco(request.user):
        messages.error(request, TEAM_ONLY_MESSAGE)
    else:
        messages.error(request, SATURDAY_ONLY_MESSAGE)
    return redirect(reverse("play", args=[slug]))


def _rosco_access_denied_response(user):
    if not user_can_see_rosco(user):
        return JsonResponse({"error": TEAM_ONLY_MESSAGE}, status=403)
    return JsonResponse({"error": SATURDAY_ONLY_MESSAGE}, status=403)


def _build_processor(request, game, mode):
    service = WeeklyRoscoService(game, mode, request.user)
    weekly_rosco = service.ensure_current_weekly_rosco()
    session = service.get_or_create_session(weekly_rosco)
    entry = service.get_entry_for_letter(weekly_rosco, session.rosco_current_letter)
    return RoscoTurnProcessor(session, weekly_rosco, entry), session


@never_cache
@login_required
@csrf_protect
def play_rosco_game(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_rosco_mode(game, mode_slug)
    blocked = _blocked_rosco_access(request, slug)
    if blocked:
        return blocked
    context = RoscoContextBuilder(request, game, mode).build()
    if context.get("rosco_unavailable"):
        messages.error(
            request,
            "El rosco Pasapalabra aún no está configurado para este juego.",
        )
        return redirect(reverse("play", args=[slug]))
    return render(request, "games/play_rosco.html", context)


@require_POST
@login_required
@never_cache
@csrf_protect
def rosco_answer(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_rosco_mode(game, mode_slug)
    if not user_can_play_rosco(request.user):
        return _rosco_access_denied_response(request.user)
    blocked = _unavailable_response(game)
    if blocked:
        return blocked
    answer_text = request.POST.get("answer", "").strip()
    if not answer_text:
        return JsonResponse({"error": "Debes escribir una respuesta."}, status=400)

    processor, session = _build_processor(request, game, mode)
    if not session_is_playable(session):
        return JsonResponse({"error": "La partida ya ha terminado."}, status=403)
    if processor.entry is None:
        return JsonResponse({"error": "No hay pregunta activa para esta letra."}, status=400)

    payload = processor.process_answer(answer_text)
    if payload.get("error"):
        return JsonResponse(payload, status=400)
    return JsonResponse(payload)


@require_POST
@login_required
@never_cache
@csrf_protect
def rosco_pass(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_rosco_mode(game, mode_slug)
    if not user_can_play_rosco(request.user):
        return _rosco_access_denied_response(request.user)
    blocked = _unavailable_response(game)
    if blocked:
        return blocked
    processor, session = _build_processor(request, game, mode)
    if not session_is_playable(session):
        return JsonResponse({"error": "La partida ya ha terminado."}, status=403)

    payload = processor.process_pass()
    if payload.get("error"):
        return JsonResponse(payload, status=400)
    return JsonResponse(payload)


@require_POST
@login_required
@never_cache
@csrf_protect
def rosco_surrender(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_rosco_mode(game, mode_slug)
    if not user_can_play_rosco(request.user):
        return _rosco_access_denied_response(request.user)
    blocked = _unavailable_response(game)
    if blocked:
        return blocked
    processor, session = _build_processor(request, game, mode)
    if not session_is_playable(session):
        return JsonResponse({"error": "La partida ya ha terminado."}, status=403)

    payload = processor.process_surrender()
    return JsonResponse(payload)
