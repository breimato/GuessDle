from django.shortcuts import render

# Create your views here.
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def dashboard_view(request):
    # Datos de ejemplo por ahora. Luego los conectamos a modelos.
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

    juegos_disponibles = ['Palabra', 'País', 'Marca']

    return render(request, 'accounts/dashboard.html', {
        'user_stats': user_stats,
        'ranking_diario': ranking_diario,
        'ranking_semanal': ranking_semanal,
        'juegos_disponibles': juegos_disponibles,
    })
