# apps/accounts/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.contrib.auth.models import User

from apps.accounts.services.dashboard_stats import DashboardStats


@never_cache
@login_required
def dashboard_view(request):
    stats = DashboardStats(request.user)
    context = {
        "juegos_disponibles": stats.available_games(),
        "user_stats": {"juegos": stats.user_stats()},
        "ranking_global": stats.ranking_global(),
        "ranking_por_juego": stats.ranking_per_game(),
    }
    return render(request, "accounts/dashboard.html", context)


def register_view(request):
    if request.method == "POST":
        username   = request.POST.get("username")
        first_name = request.POST.get("first_name")
        email = request.POST.get("email")
        password1  = request.POST.get("password1")
        password2  = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden.")
        elif User.objects.filter(username=username).exists():
            messages.error(request, "Este nickname ya está en uso.")
        else:
            User.objects.create_user(
                username=username,
                first_name=first_name,
                email=email,
                password=password1
            )
            messages.success(request, "¡Registro completado! Ahora inicia sesión.")
            return redirect("login")

    return render(request, "accounts/register.html")
