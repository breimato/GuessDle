from django.shortcuts import render

import random
from django.shortcuts import render, get_object_or_404
from apps.games.models import Game, GameItem


def play_view(request, slug):
    game = get_object_or_404(Game, slug=slug)
    all_items = list(game.items.all())
    objetivo = all_items[0]  # ⚠️ Por ahora: siempre el mismo (primer) personaje

    resultado = None
    intento = None

    if request.method == 'POST':
        intento_nombre = request.POST.get('guess')
        intento = GameItem.objects.filter(game=game, name__iexact=intento_nombre).first()

        if intento:
            resultado = []
            for atributo in game.attributes:
                valor_intento = intento.data.get(atributo)
                valor_objetivo = objetivo.data.get(atributo)
                igual = valor_intento == valor_objetivo
                resultado.append({
                    'campo': atributo,
                    'valor_intento': valor_intento,
                    'valor_objetivo': valor_objetivo,
                    'correcto': igual
                })

    return render(request, 'games/play.html', {
        'game': game,
        'intento': intento,
        'resultado': resultado
    })

