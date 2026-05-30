from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.games.models import Game
from apps.games.services.play_session.context_builder import ContextBuilder
from apps.games.views.guess_responses import PlaySessionRef, process_guess_request
from apps.games.services.daily.flow import (
    handle_daily_post,
    render_daily_play_page,
    render_missing_daily_target,
    render_mode_select,
    should_show_mode_select,
)

from apps.games.views.helpers import process_reveal_hint, resolve_play_context
from apps.games.views.rosco_views import play_rosco_game


@require_POST
@login_required
@never_cache
@csrf_protect
def process_daily_guess(request, slug: str, mode_slug=None):
    game, mode, _, daily_target = resolve_play_context(request, slug, mode_slug)
    if not daily_target:
        return JsonResponse({"error": "No daily target set."}, status=400)

    return process_guess_request(
        request,
        game,
        PlaySessionRef(daily_target=daily_target),
    )


@require_POST
@login_required
@never_cache
@csrf_protect
def reveal_daily_hint(request, slug: str, mode_slug=None):
    game, mode, _, daily_target = resolve_play_context(request, slug, mode_slug)
    if not daily_target:
        return JsonResponse({"error": "No daily target set."}, status=400)

    context = ContextBuilder(request, game, daily_target=daily_target).build()
    if not context["can_play"]:
        return JsonResponse({"error": "You cannot play anymore."}, status=403)

    return process_reveal_hint(
        request,
        game=game,
        target=daily_target.target,
        daily_target=daily_target,
    )


@never_cache
@login_required
@csrf_protect
def play_daily_game(request, slug: str, mode_slug=None):
    game = get_object_or_404(Game, slug=slug)
    user = request.user

    if should_show_mode_select(game, mode_slug):
        return render_mode_select(request, game, user, slug)

    game, mode, resolver, daily_target = resolve_play_context(request, slug, mode_slug)
    if mode and mode.is_rosco:
        return play_rosco_game(request, slug, mode_slug)

    if not daily_target:
        return render_missing_daily_target(request, game, mode)

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    if request.method == "POST":
        return handle_daily_post(request, game, daily_target, user, is_ajax)

    return render_daily_play_page(request, game, daily_target, mode, user)
