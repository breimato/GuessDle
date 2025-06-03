from __future__ import annotations

import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import now, localtime
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.accounts.models import Challenge
from apps.games.models import Game, ExtraDailyPlay, GameAttempt
from apps.games.services.gameplay.challenge_view_helper import ChallengeViewHelper
from apps.games.services.gameplay.extra_daily_service import ExtraDailyService
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.context_builder import ContextBuilder
from apps.games.services.gameplay.guess_processor import GuessProcessor
from apps.games.services.gameplay.result_updater import ResultUpdater
from apps.games.services.gameplay.target_service import TargetService

# Nuevo: ChallengeResolutionService
from apps.games.services.gameplay.challenge_resolution_service import ChallengeResolutionService

# ------------------------------------------------------------------ #
# 1) AJAX – partida diaria
# ------------------------------------------------------------------ #
@require_POST
@login_required
@never_cache
@csrf_protect
def ajax_guess(request, slug: str):
    game = get_object_or_404(Game, slug=slug)
    user = request.user

    target_service = TargetService(game, user)
    daily_target = target_service.get_target_for_today()

    if not daily_target:
        return JsonResponse({"error": "No hay objetivo diario."}, status=400)

    ctx = ContextBuilder(request, game, daily_target=daily_target).build()
    if not ctx["can_play"]:
        return JsonResponse({"error": "No puedes jugar más."}, status=403)

    valid, correct = GuessProcessor(game, user).process(request, daily_target=daily_target)
    if not valid:
        return JsonResponse({"error": "Intento inválido"}, status=400)

    ctx = ContextBuilder(request, game, daily_target=daily_target).build()
    last_attempt = ctx["attempts"][0]

    return JsonResponse({
        "won": correct,
        "attempt": {
            "name":     last_attempt["name"],
            "icon":     last_attempt.get("icon"),
            "feedback": last_attempt["feedback"],
            "guess_image_url": last_attempt.get("guess_image_url"),
        },
        "remaining_names": json.loads(ctx["remaining_names_json"]),
    })


# ------------------------------------------------------------------ #
# 2) Vista HTML – partida diaria
# ------------------------------------------------------------------ #
@never_cache
@login_required
@csrf_protect
def play_view(request, slug: str):
    game = get_object_or_404(Game, slug=slug)
    user = request.user
    target_service = TargetService(game, user)
    daily_target = target_service.get_target_for_today()

    if not daily_target:
        messages.error(request, "Todavía no se ha generado el personaje del día.")
        return render(request, "games/play.html", {"game": game})

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method == "POST":
        ctx = ContextBuilder(request, game, daily_target=daily_target).build()
        if not ctx["can_play"]:
            if is_ajax:
                return JsonResponse({"error": "No puedes jugar más."}, status=403)
            messages.error(request, "No puedes jugar más.")
            return render(request, "games/play.html", ctx)

        valid, correct = GuessProcessor(game, user).process(request, daily_target=daily_target)
        if not valid:
            if is_ajax:
                return JsonResponse({"error": "Intento inválido"}, status=400)
            messages.error(request, "Intento inválido o repetido.")
            return render(request, "games/play.html", ctx)

        ctx = ContextBuilder(request, game, daily_target=daily_target).build()
        last_attempt = ctx["attempts"][0]
        if correct:
            ctx["won"] = True
            ctx["target"] = daily_target

        if is_ajax:
            return JsonResponse({
                "won": correct,
                "attempt": {
                    "name":     last_attempt["name"],
                    "icon":     last_attempt.get("icon"),
                    "feedback": last_attempt["feedback"],
                    "guess_image_url": last_attempt.get("guess_image_url"),
                },
                "remaining_names": json.loads(ctx["remaining_names_json"]),
            })
        return render(request, "games/play.html", ctx)

    ctx = ContextBuilder(request, game, daily_target=daily_target).build()
    extras_service = ExtraDailyService(user, game)
    ctx.update({
        "slug": game.slug,
        "extra_id": None,
        "max_extras_reached": extras_service.max_reached(),
    })
    return render(request, "games/play.html", ctx)


# ------------------------------------------------------------------ #
# 3) Vista HTML – reto 1 v 1
# ------------------------------------------------------------------ #

@never_cache
@login_required
@csrf_protect
def play_challenge(request, challenge_id: int):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    helper = ChallengeViewHelper(request, challenge)

    helper.accept_if_needed()
    if not helper.ensure_participant():
        return redirect("dashboard")

    if not challenge.target:
        challenge.target = TargetService(challenge.game, request.user).get_random_item()
        challenge.save(update_fields=["target"])

    if request.method == "POST":
        if not helper.assign_attempts_from_post():
            return redirect("play_challenge", challenge_id=challenge.id)

        # SOLID: toda la lógica de resolución de retos y puntos en un solo service
        ChallengeResolutionService(challenge, acting_user=request.user).resolve_and_assign_points()
        return redirect("dashboard")

    ctx = ContextBuilder(request, challenge.game, challenge=challenge).build()
    ctx.update({
        "game": challenge.game,
        "is_challenge": True,
        "challenge_id": challenge.id,
        "background_url": (
            challenge.game.background_image.url if challenge.game.background_image else None
        ),
        "guess_url": reverse("ajax_guess_challenge", args=[challenge.id]),
        "challenge_report_url": reverse("play_challenge", args=[challenge.id]),
        "is_challenge_js": "true",
    })
    return render(request, "games/play.html", ctx)


# ------------------------------------------------------------------ #
# 4) AJAX – reto 1 v 1
# ------------------------------------------------------------------ #
@require_POST
@login_required
@never_cache
@csrf_protect
def ajax_guess_challenge(request, challenge_id: int):
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    if request.user not in (challenge.challenger, challenge.opponent):
        return JsonResponse({"error": "No autorizado."}, status=403)

    game = challenge.game
    ctx = ContextBuilder(request, game, challenge=challenge).build()
    if not ctx["can_play"]:
        return JsonResponse({"error": "No puedes jugar más."}, status=403)

    valid, correct = GuessProcessor(game, request.user).process(request, challenge=challenge)
    if not valid:
        return JsonResponse({"error": "Intento inválido"}, status=400)

    ctx = ContextBuilder(request, game, challenge=challenge).build()
    last_attempt = ctx["attempts"][0]

    return JsonResponse({
        "won": correct,
        "attempt": {
            "name":     last_attempt["name"],
            "icon":     last_attempt.get("icon"),
            "feedback": last_attempt["feedback"],
            "guess_image_url": last_attempt.get("guess_image_url"),
        },
        "remaining_names": json.loads(ctx["remaining_names_json"]),
    })


# ------------------------------------------------------------------ #
# 5) Iniciar partida extra diaria (POST)
# ------------------------------------------------------------------ #
@login_required
@csrf_protect
def start_extra_daily(request, slug: str):
    game = get_object_or_404(Game, slug=slug)
    user = request.user
    extras_service = ExtraDailyService(user, game)

    if extras_service.max_reached():
        messages.error(request, "Ya has jugado el máximo de 2 partidas extra hoy en este juego.")
        return redirect("dashboard")

    try:
        bet = float(request.POST.get("bet", "0"))
    except ValueError:
        bet = 0

    try:
        extra = extras_service.start_extra_play(bet)
    except ValueError as err:
        messages.error(request, str(err))
        return redirect("dashboard")

    return redirect("play_extra_daily", extra_id=extra.id)


# ------------------------------------------------------------------ #
# 6) Vista HTML – partida extra diaria
# ------------------------------------------------------------------ #
@login_required
@csrf_protect
def play_extra_daily(request, extra_id: int):
    extra = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user, completed=False)
    game = extra.game
    extras_service = ExtraDailyService(request.user, game)

    target_service = TargetService(game, request.user)
    if not target_service.is_daily_resolved():
        return redirect("play", slug=game.slug)

    if localtime(extra.created_at).date() != date.today():
        return redirect("dashboard")

    if request.method == "POST":
        valid, correct = GuessProcessor(game, request.user).process(request, extra_play=extra)
        if valid and correct:
            ResultUpdater(game, request.user).update_for_game(extra_play=extra)
            extra.completed = True
            extra.save(update_fields=["completed"])

    ctx = ContextBuilder(request, game, extra_play=extra).build()
    ctx.update({
        "target": extra.target,
        "guess_url": reverse("ajax_guess_extra", args=[extra.id]),
        "slug": game.slug,
        "extra_id": extra.id,
        "max_extras_reached": extras_service.max_reached(),
    })
    return render(request, "games/play.html", ctx)


# ------------------------------------------------------------------ #
# 7) AJAX – partida extra diaria
# ------------------------------------------------------------------ #
@require_POST
@login_required
@never_cache
@csrf_protect
def ajax_guess_extra(request, extra_id: int):
    extra = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    game = extra.game

    ctx = ContextBuilder(request, game, extra_play=extra).build()
    if not ctx["can_play"]:
        return JsonResponse({"error": "No puedes jugar más."}, status=403)

    valid, correct = GuessProcessor(game, request.user).process(request, extra_play=extra)
    if not valid:
        return JsonResponse({"error": "Intento inválido"}, status=400)

    ctx = ContextBuilder(request, game, extra_play=extra).build()
    last_attempt = ctx["attempts"][0]

    return JsonResponse({
        "won": correct,
        "attempt": {
            "name":     last_attempt["name"],
            "icon":     last_attempt.get("icon"),
            "feedback": last_attempt["feedback"],
            "guess_image_url": last_attempt.get("guess_image_url"),
        },
        "remaining_names": json.loads(ctx["remaining_names_json"]),
    })
