# apps/games/views.py

from tkinter import E
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.urls import reverse
import json

from apps.accounts.models import Challenge
from apps.accounts.services.elo import Elo
from apps.games.models import Game, ExtraDailyPlay
from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.context_builder import ContextBuilder
from apps.games.services.gameplay.result_updater import ResultUpdater
from apps.games.services.gameplay.target_service import TargetService
from apps.games.services.gameplay.guess_processor import GuessProcessor

# ------------------------------------------------------------------ #
# 1) AJAX – partida diaria
# ------------------------------------------------------------------ #
@require_POST
@login_required
@never_cache
@csrf_protect
def ajax_guess(request, slug):
    game = get_object_or_404(Game, slug=slug)
    target_service = TargetService(game, request.user)
    daily_target = target_service.get_target_for_today()

    if not daily_target:
        return JsonResponse({"error": "No hay objetivo diario."}, status=400)

    ctx = ContextBuilder(request, game, daily_target=daily_target).build()
    if not ctx["can_play"]:
        return JsonResponse({"error": "No puedes jugar más."}, status=403)

    valid, correct = GuessProcessor(game, request.user).process(request, daily_target=daily_target)
    if not valid:
        return JsonResponse({"error": "Intento inválido"}, status=400)

    # reconstruir contexto con el nuevo intento
    ctx = ContextBuilder(request, game, daily_target=daily_target).build()
    if not ctx["attempts"]:
        return JsonResponse({"error": "No hay intentos registrados"}, status=500)

    last_attempt = ctx["attempts"][0]

    return JsonResponse({
        "won": correct,
        "attempt": {
            "name":     last_attempt["name"],
            "icon":     last_attempt["icon"],
            "feedback": last_attempt["feedback"],
        },
        "remaining_names": json.loads(ctx["remaining_names_json"]),
    })


# ------------------------------------------------------------------ #
# 2) Vista HTML – partida diaria
# ------------------------------------------------------------------ #
@never_cache
@login_required
@csrf_protect
def play_view(request, slug):
    game = get_object_or_404(Game, slug=slug)
    target_service = TargetService(game, request.user)
    daily_target = target_service.get_target_for_today()

    if not daily_target:
        messages.error(request, "Todavía no se ha generado el personaje del día.")
        return render(request, "games/play.html", {"game": game})

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    # ------------------- POST ------------------- #
    if request.method == "POST":
        ctx = ContextBuilder(request, game, daily_target=daily_target).build()

        if not ctx["can_play"]:
            if is_ajax:
                return JsonResponse({"error": "No puedes jugar más."}, status=403)
            messages.error(request, "No puedes jugar más.")
            return render(request, "games/play.html", ctx)

        valid, correct = GuessProcessor(game, request.user).process(request, daily_target=daily_target)

        if not valid:
            if is_ajax:
                return JsonResponse({"error": "Intento inválido"}, status=400)
            messages.error(request, "Intento inválido o repetido.")
            return render(request, "games/play.html", ctx)

        if is_ajax:
            ctx = ContextBuilder(request, game, daily_target=daily_target).build()
            last_attempt = ctx["attempts"][0]
            return JsonResponse({
                "won": correct,
                "attempt": {
                    "name": last_attempt["name"],
                    "icon": last_attempt["icon"],
                    "feedback": last_attempt["feedback"],
                }
            })

        return render(request, "games/play.html", ctx)

    # ------------------- GET ------------------- #
    ctx = ContextBuilder(request, game, daily_target=daily_target).build()
    return render(request, "games/play.html", ctx)


# ------------------------------------------------------------------ #
# 3) Vista HTML – reto 1 v 1
# ------------------------------------------------------------------ #
@never_cache
@login_required
@csrf_protect
def play_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    manager = ChallengeManager(request, challenge)

    manager.accept_if_needed()
    if not manager.ensure_participant():
        return redirect("dashboard")

    # Crear target si falta
    if not challenge.target:
        challenge.target = TargetService(challenge.game, request.user).get_random_item()
        challenge.save()

    # POST: guardar intentos
    if request.method == "POST":
        if not manager.assign_attempts_from_post():
            return redirect("play_challenge", challenge_id=challenge.id)
        manager.resolve_if_ready()
        return redirect("dashboard")

    # GET: construir contexto y renderizar
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
def ajax_guess_challenge(request, challenge_id):
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
            "icon":     last_attempt["icon"],
            "feedback": last_attempt["feedback"],
        },
        "remaining_names": json.loads(ctx["remaining_names_json"]),
    })


@login_required
@csrf_protect
def start_extra_daily(request, slug):
    game = get_object_or_404(Game, slug=slug)
    user = request.user

    try:
        bet = float(request.POST.get("bet", "0"))
    except ValueError:
        bet = 0

    elo = Elo(user, game)

    if bet <= 0 or elo.elo_obj.elo < bet:
        messages.error(request, "Apuesta inválida o sin suficiente ELO.")
        return redirect("dashboard")

    # 💰 Restamos el ELO
    elo.elo_obj.elo -= bet
    elo.elo_obj.save(update_fields=["elo"])

    target = TargetService(game, user).get_random_item()

    # 🔐 Guardamos la apuesta directamente en la BBDD
    extra = ExtraDailyPlay.objects.create(user=user, game=game, target=target, bet_amount=bet)

    return redirect("play_extra_daily", extra_id=extra.id)


@login_required
@csrf_protect
def play_extra_daily(request, extra_id):
    extra = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    game = extra.game

    session_key = f"extra_bet_{extra.id}"

    # Verifica si ya ha ganado
    valid, correct = GuessProcessor(game, request.user).process(request, extra_play=extra)
    if valid and correct:
        ResultUpdater(game, request.user).update_for_game(extra_play=extra)

        bet = ExtraDailyPlay.objects.filter(pk=extra.id, user=request.user).get().bet_amount

        # ➕ lógica de apuesta personalizada
        if bet:
            gain = float(bet) + (float(bet) * 0.5)
            elo = Elo(request.user, game)
            elo.elo_obj.elo += gain
            elo.elo_obj.save(update_fields=["elo"])

    # 🧠 Aquí usamos extra_play=extra explícitamente
    ctx = ContextBuilder(request, game, extra_play=extra).build()
    ctx["target"] = extra.target
    ctx["guess_url"] = reverse("ajax_guess_extra", args=[extra.id])
    return render(request, "games/play.html", ctx)




@require_POST
@login_required
@never_cache
@csrf_protect
def ajax_guess_extra(request, extra_id):
    extra = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    game = extra.game

    ctx = ContextBuilder(request, game, extra_play=extra).build()
    ctx["target"] = extra.target

    if not ctx["can_play"]:
        return JsonResponse({"error": "No puedes jugar más."}, status=403)

    valid, correct = GuessProcessor(game, request.user).process(
        request, extra_play=extra
    )
    if not valid:
        return JsonResponse({"error": "Intento inválido"}, status=400)

    ctx = ContextBuilder(request, game, extra_play=extra).build()
    ctx["target"] = extra.target

    last_attempt = ctx["attempts"][0]

    return JsonResponse({
        "won": correct,
        "attempt": {
            "name": last_attempt["name"],
            "icon": last_attempt["icon"],
            "feedback": last_attempt["feedback"],
        },
        "remaining_names": json.loads(ctx["remaining_names_json"]),
    })
