
# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib import messages
from django.views.decorators.cache import never_cache

from apps.games.models import Game


@never_cache
@login_required
def dashboard_view(request):
    # Datos de ejemplo por ahora. Luego los conectamos a modelos.
    available_games = Game.objects.filter(active=True)

    user_stats = {
        'juegos': [
            {'nombre': 'Palabra', 'media_tiempo': 4.5},
            {'nombre': 'País', 'media_tiempo': 6.2},
            {'nombre': 'Marca', 'media_tiempo': 3.9},
        ]
    }

    ranking_diario = [
        {'username': 'Kakashi', 'puntos': 120},
        {'username': 'Naruto', 'puntos': 110},
        {'username': 'Sakura', 'puntos': 95},
    ]

    ranking_semanal = [
        {'username': 'Itachi', 'puntos': 700},
        {'username': 'Madara', 'puntos': 630},
        {'username': 'Hinata', 'puntos': 590},
    ]

    return render(request, 'accounts/dashboard.html', {
        'user_stats': user_stats,
        'ranking_diario': ranking_diario,
        'ranking_semanal': ranking_semanal,
        'juegos_disponibles': available_games,
    })


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