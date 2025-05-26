from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import Challenge
from apps.games.models import Game, DailyTarget
from apps.games.services.gameplay import get_current_target, process_guess, build_context


@never_cache
@login_required
@csrf_protect
def play_view(request, slug):
    game = get_object_or_404(Game, slug=slug)
    target, daily = get_current_target(game, request.user)

    # ⚠️ Safety: si no existe el DailyTarget (por error o falta del cron)
    if not daily:
        messages.error(request, "Todavía no se ha generado el personaje del día.")
        return render(request, "games/play.html", {"game": game})

    # ⏱️ Procesar intento si es POST
    if request.method == "POST" and build_context(request, game, daily)["can_play"]:
        valid, correct = process_guess(request, game, daily)
        if not valid:
            messages.error(request, "Intento inválido o repetido.")
        return redirect("play", slug=slug)

    # 🧠 Construir contexto normal de juego
    ctx = build_context(request, game, daily)
    ctx["background_url"] = game.background_image.url if game.background_image else None

    # 👈 Mostrar el personaje de ayer, respetando si es una cuenta de equipo
    yesterday_date = daily.date - timedelta(days=1)

    profile = getattr(request.user, "profile", None)
    is_team = getattr(profile, "is_team_account", False)

    yesterday_target = (
        DailyTarget.objects
        .filter(
            game=game,
            date=yesterday_date,
            is_team=is_team  # 👈 clave: que coincida con la lógica de ese día
        )
        .select_related("target")
        .first()
    )

    if yesterday_target:
        ctx["yesterday_target_name"] = yesterday_target.target.name

    return render(request, "games/play.html", ctx)


@never_cache
@login_required
@csrf_protect
# VISTA PARA JUGAR EL RETO
def play_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)

    # Solo el oponente puede aceptar el reto si no ha sido aceptado aún
    if not challenge.accepted and challenge.opponent == request.user:
        challenge.accepted = True
        challenge.save()

    # Restringir el acceso solo a los participantes
    if request.user != challenge.challenger and request.user != challenge.opponent:
        return redirect("dashboard")

    game = challenge.game
    return render(request, 'games/play.html', {
        'game': game,
        'is_challenge': True,
        'challenge_id': challenge.id
    })
