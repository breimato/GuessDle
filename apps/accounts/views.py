
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.timezone import now
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.models import User
from django.db import models, transaction
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.views import LoginView as DjangoLoginView
from apps.accounts.models import UserProfile, Challenge
from apps.accounts.services.dashboard_stats import DashboardStats
from apps.accounts.services.score_service import ScoreService
from apps.common.utils import json_success
from apps.games.models import Game, ExtraDailyPlay
from apps.games.services.gameplay.target_service import TargetService
from django.contrib.auth.models import User
from django.urls import reverse
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models import Challenge
from apps.accounts.services.score_service import ScoreService
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.games.models import GameAttempt
from apps.common.utils import json_success, json_error



from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from apps.accounts.models import Challenge


# apps/accounts/views.py  (o donde tengas el resto)
from django.views.decorators.http import require_POST

# apps/accounts/views.py
from django.http import JsonResponse
from django.template.loader import render_to_string
# … resto de imports …

# ---------- CREAR RETO ----------
@login_required
@csrf_protect
def create_challenge(request):
    if request.method != "POST":
        return json_error("Método no permitido", 405)

    opponent_id = request.POST.get("opponent")
    game_id     = request.POST.get("game")

    opponent = get_object_or_404(User, pk=opponent_id)
    game     = get_object_or_404(Game, pk=game_id)

    exists = Challenge.objects.filter(
        challenger=request.user,
        opponent=opponent,
        game=game,
        accepted=False,
        completed=False
    ).exists()
    if exists:
        return json_error("Ese reto ya existe")

    with transaction.atomic():
        target = TargetService(game, request.user).get_random_item()
        challenge = Challenge.objects.create(
            challenger=request.user,
            opponent=opponent,
            game=game,
            target=target
        )

    # devolvemos la tarjeta HTML lista para insertar
    card_html = render_to_string(
        "partials/sent_challenge_card.html",
        {"challenge": challenge},
        request=request
    )
    return json_success({"card": card_html})


# ---------- CANCELAR (yo lo envié) ----------
@require_POST
@login_required
def cancelar_challenge(request, challenge_id):
    challenge = get_object_or_404(
        Challenge,
        id=challenge_id,
        challenger=request.user,
        accepted=False,
        completed=False
    )
    challenge.delete()
    return json_success({"id": challenge_id})


# ---------- RECHAZAR (me lo enviaron) ----------
@require_POST
@login_required
def rechazar_challenge(request, challenge_id):
    challenge = get_object_or_404(
        Challenge,
        id=challenge_id,
        opponent=request.user,
        accepted=False,
        completed=False
    )
    challenge.delete()
    return json_success({"id": challenge_id})


@never_cache
@login_required
def dashboard_view(request):
    stats = DashboardStats(request.user)
    users = User.objects.exclude(id=request.user.id)

    pending_challenges = Challenge.objects.filter(opponent=request.user, accepted=False)
    active_challenges = Challenge.objects.filter(
        accepted=True,
        completed=False
    ).filter(models.Q(challenger=request.user) | models.Q(opponent=request.user))
    active_challenges_to_play = Challenge.objects.filter(
        accepted=True,
        completed=False
    ).filter(
        challenger=request.user
        # aquí puedes añadir más lógica si necesitas comprobar si tú has jugado tu parte
    )
    sent_pending_challenges = Challenge.objects.filter(
        challenger=request.user,
        accepted=False,
        completed=False
        )


    today = now().date()

    # 🚀 1. Mapea slug → extra_id (solo de hoy)
    active_extras = ExtraDailyPlay.objects.filter(
        user=request.user,
        completed=False,
        created_at__date=today  # ✅ solo de hoy
    ).select_related('game')

    extras_by_slug = {extra.game.slug: extra.id for extra in active_extras}

    # 🚀 2. Mapea slug → has_daily_target
    juegos_disponibles = stats.available_games()
    daily_targets_by_slug = {
        game.slug: bool(not TargetService(game, request.user).is_daily_resolved())
        for game in juegos_disponibles
    }

    # 🚀 3. Annotamos cada juego con redirección lógica
    for juego in juegos_disponibles:
        if daily_targets_by_slug.get(juego.slug):
            juego.redirect_url = reverse("play", args=[juego.slug])  # 🎯 prioridad a daily
        elif juego.slug in extras_by_slug:
            juego.redirect_url = reverse("play_extra_daily", args=[extras_by_slug[juego.slug]])
        else:
            juego.redirect_url = reverse("play", args=[juego.slug])  # fallback

    context = {
        "juegos_disponibles": juegos_disponibles,
        "user_stats": {
            "juegos": stats.user_stats(),
            "elo_global": stats.elo_global(),
        },
        "ranking_global": stats.ranking_global(),
        "ranking_por_juego": stats.ranking_per_game(),
        "pending_challenges": pending_challenges,
        "active_challenges": active_challenges,
        "active_challenges_to_play": active_challenges_to_play,
        "sent_pending_challenges": sent_pending_challenges,
        "users": users,
    }

    return render(request, "accounts/dashboard.html", context)




def register_view(request):
    if request.method != "POST":
        return render(request, "accounts/register.html")

    username   = request.POST.get("username")
    first_name = request.POST.get("first_name")
    email      = request.POST.get("email")
    password1  = request.POST.get("password1")
    password2  = request.POST.get("password2")
    is_team_account = request.POST.get("is_team_account") == "on"

    for field in [username, first_name, email, password1, password2]:
        if not field or field.strip() == "":
            messages.error(request, "Todos los campos son obligatorios.")
            return render(request, "accounts/register.html")

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "El email no tiene un formato válido.")
        return render(request, "accounts/register.html")

    if password1 != password2:
        messages.error(request, "Las contraseñas no coinciden.")
        return render(request, "accounts/register.html")

    if User.objects.filter(username=username).exists():
        messages.error(request, "Este nickname ya está en uso.")
        return render(request, "accounts/register.html")

    if User.objects.filter(email=email).exists():
        messages.error(request, "Ya existe una cuenta con este email.")
        return render(request, "accounts/register.html")

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        email=email,
        password=password1
    )

    user.profile.is_team_account = is_team_account
    user.profile.save()

    messages.success(request, "¡Registro completado! Ahora inicia sesión.")
    return redirect("login")



@login_required
@csrf_protect
def complete_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, pk=challenge_id, accepted=True, completed=False)

    # Determinar ganador y perdedor
    winner = request.user
    loser = challenge.opponent if challenge.challenger == winner else challenge.challenger

    # 1️⃣ Obtenemos la sesión de CHALLENGE para cada jugador
    session_winner = PlaySessionService.get_or_create(
        winner,
        challenge.game,
        challenge=challenge
    )
    session_loser = PlaySessionService.get_or_create(
        loser,
        challenge.game,
        challenge=challenge
    )

    # 2️⃣ Contamos intentos en cada sesión
    attempts_winner = GameAttempt.objects.filter(session=session_winner).count()
    attempts_loser  = GameAttempt.objects.filter(session=session_loser).count()

    # 3️⃣ Asignamos puntos al ganador según sus intentos
    score_winner = ScoreService(winner, challenge.game)
    pts_ganados   = score_winner.add_points_for_attempts(attempts_winner)

    # (Opcional: si quieres dar puntos al perdedor, descomenta
    # score_loser = ScoreService(loser, challenge.game)
    # pts_perdedor = score_loser.add_points_for_attempts(attempts_loser)
    # Pero por ahora, el perdedor no recibe puntos.)

    # 4️⃣ Guardar resultado del challenge
    challenge.completed = True
    challenge.winner   = winner
    challenge.save()

    return JsonResponse({
        "status": "success",
        "winner": winner.username,
        "points_awarded": pts_ganados,
    })


class LoginView(DjangoLoginView):
    template_name = "registration/login.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        remember_me = self.request.POST.get('remember_me')
        if remember_me:
            self.request.session.set_expiry(1209600)  # 2 semanas
        else:
            self.request.session.set_expiry(0)  # Hasta cerrar el navegador
        return response