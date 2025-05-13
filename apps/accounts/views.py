
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.cache import never_cache
from django.db import models          # ← añade esto

from apps.games.models import Game


from django.db.models import Avg, Count
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.games.models import Game, GameResult


@never_cache
@login_required
def dashboard_view(request):
    # 1. Juegos activos (para selector y para rankings por juego)
    available_games = Game.objects.filter(active=True).order_by("name")

    # 2. Estadísticas del usuario (ejemplo rápido: media por juego)
    #    Ajusta a tu propio cálculo cuando quieras algo distinto.
    user_stats = {
        "juegos": (
            GameResult.objects.filter(user=request.user)
                              .values(nombre=models.F("game__name"))
                              .annotate(media_tiempo=Avg("attempts"))
                              .order_by("nombre")
        )
    }

    # 3. Ranking GLOBAL   (media de intentos / nº partidas)
    ranking_global = (
        GameResult.objects.values("user__username")
                  .annotate(
                      media=Avg("attempts"),
                      partidas=Count("id")
                  )
                  .order_by("media", "user__username")
    )

    # 4. Ranking por juego  →   dict { slug: queryset }
    ranking_por_juego = {}
    for game in available_games:
        ranking_por_juego[game.slug] = (
            GameResult.objects.filter(game=game)
                      .values("user__username")
                      .annotate(
                          media=Avg("attempts"),
                          partidas=Count("id")
                      )
                      .order_by("media", "user__username")
        )

    context = {
        "user_stats": user_stats,
        "juegos_disponibles": available_games,
        "ranking_global": ranking_global,
        "ranking_por_juego": ranking_por_juego,
    }
    return render(request, "accounts/dashboard.html", context)


def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        first_name = request.POST.get('first_name')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, 'Este nickname ya está en uso.')
        else:
            user = User.objects.create_user(
                username=username,
                first_name=first_name,
                password=password1
            )
            messages.success(request, '¡Registro completado! Ahora inicia sesión.')
            return redirect('login')

    return render(request, 'accounts/register.html')