from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
import json
from django.urls import reverse


from django.views.decorators.http import require_POST

from apps.accounts.models import Challenge
from apps.accounts.services.elo import Elo
from apps.games.models import Game, DailyTarget
from apps.games.services.gameplay import (
    get_current_target,
    process_guess,
    build_context
)

# ------------------------------------------------------------------ #
# 1) AJAX – partida diaria
# ------------------------------------------------------------------ #
@require_POST
@login_required
@never_cache
@csrf_protect
def ajax_guess(request, slug):
    game = get_object_or_404(Game, slug=slug)
    target_item, daily_target = get_current_target(game, request.user)

    if not daily_target:
        return JsonResponse({"error": "No hay objetivo diario."}, status=400)

    ctx = build_context(request, game, daily_target=daily_target)
    if not ctx["can_play"]:
        return JsonResponse({"error": "No puedes jugar más."}, status=403)

    valid, correct = process_guess(request, game, daily_target)  # sigue ok
    if not valid:
        return JsonResponse({"error": "Intento inválido"}, status=400)

    # reconstruir contexto con el nuevo intento
    ctx = build_context(request, game, daily_target=daily_target)
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
    target_item, daily_target = get_current_target(game, request.user)

    if not daily_target:
        messages.error(request, "Todavía no se ha generado el personaje del día.")
        return render(request, "games/play.html", {"game": game})

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    # ------------------- POST ------------------- #
    if request.method == "POST":
        ctx = build_context(request, game, daily_target=daily_target)

        if ctx["can_play"]:
            valid, correct = process_guess(request, game, daily_target)
            if is_ajax:
                if not valid:
                    return JsonResponse({"error": "Intento inválido"}, status=400)

                last_attempt = ctx["attempts"][-1]
                return JsonResponse({
                    "won": correct,
                    "attempt": {
                        "name":     last_attempt["name"],
                        "icon":     last_attempt["icon"],
                        "feedback": last_attempt["feedback"],
                    }
                })

            if not valid:
                messages.error(request, "Intento inválido o repetido.")

        ctx["guess_url"] = reverse("ajax_guess", args=[game.slug])
        return render(request, "games/play.html", ctx)

    # ------------------- GET ------------------- #
    ctx = build_context(request, game, daily_target=daily_target)
    ctx["background_url"] = (
        game.background_image.url if game.background_image else None
    )

    # Personaje de ayer
    yesterday_date = daily_target.date - timedelta(days=1)
    profile = getattr(request.user, "profile", None)
    is_team = getattr(profile, "is_team_account", False)

    yesterday_target = (
        DailyTarget.objects
        .filter(game=game, date=yesterday_date, is_team=is_team)
        .select_related("target")
        .first()
    )
    if yesterday_target:
        ctx["yesterday_target_name"] = yesterday_target.target.name

    return render(request, "games/play.html", ctx)


# ------------------------------------------------------------------ #
# 3) Vista HTML – reto 1 v 1
# ------------------------------------------------------------------ #
@never_cache
@login_required
@csrf_protect
def play_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Solo el oponente puede aceptar el reto si no ha sido aceptado aún
    if not challenge.accepted and challenge.opponent == request.user:
        challenge.accepted = True
        challenge.save()

    # Restringir acceso
    if request.user not in (challenge.challenger, challenge.opponent):
        return redirect("dashboard")

    # Generar target si no lo tiene
    if not challenge.target:
        from apps.games.services.gameplay import get_random_item
        challenge.target = get_random_item(challenge.game)
        challenge.save()

    ctx = build_context(request, challenge.game, challenge=challenge)
    ctx.update({
        "game": challenge.game,
        "is_challenge": True,
        "challenge_id": challenge.id,
        "background_url": (
            challenge.game.background_image.url
            if challenge.game.background_image else None
        ),
    })

    # ------------------- POST – guardar intentos ------------------- #
    if request.method == "POST":
        try:
            attempts = int(request.POST.get("attempts"))
        except (TypeError, ValueError):
            messages.error(request, "Número de intentos inválido.")
            return redirect("play_challenge", challenge_id=challenge.id)

        if request.user == challenge.challenger:
            challenge.challenger_attempts = attempts
        else:
            challenge.opponent_attempts = attempts

        challenge.save()

        # Resolver reto cuando ambos jugaron
        if (
            challenge.challenger_attempts is not None and
            challenge.opponent_attempts is not None and
            not challenge.completed
        ):
            if challenge.challenger_attempts < challenge.opponent_attempts:
                winner, loser = challenge.challenger, challenge.opponent
            elif challenge.opponent_attempts < challenge.challenger_attempts:
                winner, loser = challenge.opponent, challenge.challenger
            else:
                winner = loser = None   # empate

            if winner:
                Elo(winner, challenge.game).update_vs_opponent(
                    result=1,
                    opponent_rating=Elo(loser, challenge.game).elo_obj.elo
                )
                Elo(loser, challenge.game).update_vs_opponent(
                    result=0,
                    opponent_rating=Elo(winner, challenge.game).elo_obj.elo
                )
                challenge.winner = winner
                challenge.elo_exchanged = True

            challenge.completed = True
            challenge.save()

        return redirect("dashboard")

    from django.urls import reverse

    ctx.update({
        "guess_url": reverse("ajax_guess_challenge", args=[challenge.id]),
        "challenge_report_url": reverse("play_challenge", args=[challenge.id]),
        "is_challenge_js": "true",  # importante para el JS
    })

    return render(request, "games/play.html", ctx)


@require_POST
@login_required
@never_cache
@csrf_protect
def ajax_guess_challenge(request, challenge_id):
    """
    Recibe un intento dentro de un reto 1 v 1.
    """
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    if request.user not in (challenge.challenger, challenge.opponent):
        return JsonResponse({"error": "No autorizado."}, status=403)

    game = challenge.game

    ctx = build_context(request, game, challenge=challenge)
    if not ctx["can_play"]:
        return JsonResponse({"error": "No puedes jugar más."}, status=403)

    valid, correct = process_guess(request, game, challenge=challenge)
    if not valid:
        return JsonResponse({"error": "Intento inválido"}, status=400)

    # Reconstruir contexto con el nuevo intento
    ctx = build_context(request, game, challenge=challenge)
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
