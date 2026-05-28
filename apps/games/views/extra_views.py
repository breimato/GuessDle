from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import localtime
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.games.models import ExtraDailyPlay, Game
from apps.games.services.play_session.context_builder import ContextBuilder
from apps.games.services.extra.extra_daily_service import ExtraDailyService
from apps.games.services.play_session.guess_processor import GuessProcessor
from apps.games.services.daily.target_service import TargetService
from apps.games.views.guess_responses import PlaySessionRef, process_guess_request
from apps.games.services.catalog.mode_resolver import ModeResolver

from apps.games.views.helpers import process_reveal_hint


@login_required
@csrf_protect
def start_extra_daily_game(request, slug: str, mode_slug=None):
    game = get_object_or_404(Game, slug=slug)
    resolver = ModeResolver(game)
    mode = resolver.resolve(mode_slug) if mode_slug else None
    if resolver.has_modes() and not mode:
        return redirect("play", slug=slug)

    user = request.user
    extra_daily_service = ExtraDailyService(user, game, mode=mode)

    if extra_daily_service.max_reached():
        messages.error(
            request,
            "You have already played the maximum of 2 extra games today for this game.",
        )
        return redirect("dashboard")

    target_service = TargetService(game, user, mode=mode)
    if not target_service.is_daily_resolved():
        messages.error(
            request,
            "Debes completar la partida diaria antes de apostar una partida extra.",
        )
        if mode:
            return redirect("play_mode", slug=slug, mode_slug=mode.slug)
        return redirect("play", slug=slug)

    try:
        bet = float(request.POST.get("bet", "0"))
    except ValueError:
        bet = 0

    try:
        extra_play = extra_daily_service.start_extra_play(bet)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("dashboard")

    return redirect("play_extra_daily", extra_id=extra_play.id)


@login_required
@csrf_protect
def play_extra_daily_game(request, extra_id: int):
    extra_play = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    game = extra_play.game
    extra_daily_service = ExtraDailyService(request.user, game, mode=extra_play.mode)

    if localtime(extra_play.created_at).date() != date.today():
        return redirect("dashboard")

    points_data = {}
    if request.method == "POST":
        if extra_play.completed:
            return redirect("play_extra_daily", extra_id=extra_play.id)
        _, _, points_data = GuessProcessor(game, request.user).process(
            request, extra_play=extra_play
        )

    context = ContextBuilder(request, game, extra_play=extra_play).build()
    context.update(
        {
            "target": extra_play.target,
            "guess_url": reverse("ajax_guess_extra", args=[extra_play.id]),
            "slug": game.slug,
            "extra_id": extra_play.id,
            "max_extras_reached": extra_daily_service.max_reached(),
        }
    )
    if points_data:
        context.update(points_data)
    return render(request, "games/play.html", context)


@require_POST
@login_required
@never_cache
@csrf_protect
def process_extra_guess(request, extra_id: int):
    extra_play = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    return process_guess_request(
        request,
        extra_play.game,
        PlaySessionRef(extra_play=extra_play),
    )


@require_POST
@login_required
@never_cache
@csrf_protect
def reveal_extra_hint(request, extra_id: int):
    extra_play = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    game = extra_play.game

    context = ContextBuilder(request, game, extra_play=extra_play).build()
    if not context["can_play"]:
        return JsonResponse({"error": "You cannot play anymore."}, status=403)

    return process_reveal_hint(
        request,
        game=game,
        target=extra_play.target,
        extra_play=extra_play,
    )
