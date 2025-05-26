# apps/accounts/views.py
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.models import User

from apps.accounts.models import UserProfile, Challenge
from apps.accounts.services.dashboard_stats import DashboardStats
from apps.accounts.services.elo import Elo
from apps.games.models import Game


@never_cache
@login_required
def dashboard_view(request):
    stats = DashboardStats(request.user)
    pending_challenges = Challenge.objects.filter(opponent=request.user, accepted=False)
    users = User.objects.exclude(id=request.user.id)

    context = {
        "juegos_disponibles": stats.available_games(),
        "user_stats": {
            "juegos": stats.user_stats(),
            "elo_global": stats.elo_global(),
        },
        "ranking_global": stats.ranking_global(),
        "ranking_por_juego": stats.ranking_per_game(),
        "pending_challenges": pending_challenges,
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



def complete_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, pk=challenge_id, accepted=True, completed=False)

    # Lógica de determinar ganador
    winner = request.user
    loser = challenge.opponent if challenge.challenger == winner else challenge.challenger

    elo_winner = Elo(winner, challenge.game)
    elo_loser = Elo(loser, challenge.game)

    # Actualización cruzada de ELO
    elo_winner.update_vs_opponent(result=1, opponent_rating=elo_loser.elo_obj.elo)
    elo_loser.update_vs_opponent(result=0, opponent_rating=elo_winner.elo_obj.elo)

    challenge.completed = True
    challenge.winner = winner
    challenge.elo_exchanged = True
    challenge.save()

    return JsonResponse({
        "status": "success",
        "winner": winner.username,
        "elo": {
            winner.username: elo_winner.elo_obj.elo,
            loser.username: elo_loser.elo_obj.elo
        }
    })


def create_challenge(request):
    if request.method == "POST":
        opponent_id = request.POST.get("opponent")
        game_id = request.POST.get("game")

        opponent = get_object_or_404(User, pk=opponent_id)
        game = get_object_or_404(Game, pk=game_id)

        # Evitar duplicados de retos no aceptados entre los mismos jugadores y juego
        if Challenge.objects.filter(challenger=request.user, opponent=opponent, game=game, accepted=False).exists():
            return redirect("dashboard")

        Challenge.objects.create(
            challenger=request.user,
            opponent=opponent,
            game=game
        )
        return redirect("dashboard")

    return redirect("dashboard")
