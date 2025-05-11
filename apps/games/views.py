import random
from django.shortcuts import render, get_object_or_404, redirect
from apps.games.models import Game, GameItem
from django.views.decorators.csrf import csrf_protect


import re

def parse_number(value):
    try:
        # Quitar todo lo que no sea número o coma/punto
        cleaned = re.sub(r"[^\d.,\-]", "", str(value))

        # Si hay más de un punto o más de una coma, probablemente son separadores de miles
        # Eliminamos todos los puntos (.) si también hay coma (,) → formato europeo
        if cleaned.count(",") == 1 and cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")
            cleaned = cleaned.replace(",", ".")  # Convertir a float

        # Eliminamos puntos si solo hay puntos y más de uno
        elif cleaned.count(".") > 1:
            cleaned = cleaned.replace(".", "")

        return float(cleaned)
    except Exception:
        return None


@csrf_protect
def play_view(request, slug):
    game = get_object_or_404(Game, slug=slug)
    all_items = list(game.items.all())

    # Setup de sesión
    if 'target_id' not in request.session or request.session.get('target_game') != game.id:
        target = random.choice(all_items)
        request.session['target_id'] = target.id
        request.session['target_game'] = game.id
        request.session['guesses'] = []
        request.session['won'] = False
    else:
        target = GameItem.objects.get(id=request.session['target_id'])

    guesses_ids = request.session.get('guesses', [])
    previous_guesses_raw = GameItem.objects.filter(id__in=guesses_ids)
    previous_guesses = sorted(previous_guesses_raw, key=lambda x: guesses_ids.index(x.id), reverse=True)
    won = request.session.get('won', False)

    guess_error = False
    guess_name = ""
    guess_item = None

    if request.method == 'POST' and not won:
        guess_name = request.POST.get('guess', '').strip()
        guess_item = game.items.filter(name__iexact=guess_name).first()

        if not guess_item or guess_item.id in guesses_ids:
            guess_error = True
        else:
            guesses_ids.append(guess_item.id)
            request.session['guesses'] = guesses_ids

            if guess_item.name == target.name:
                request.session['won'] = True
                won = True

    # Preparamos feedback ya calculado
    formatted_attempts = []
    for item in previous_guesses:
        attempt = {
            'name': item.name,
            'es_objetivo': item.name == target.name,
            'feedback': []
        }
        for atributo in game.attributes:
            valor = item.data.get(atributo)
            esperado = target.data.get(atributo)
            correcto = valor == esperado

            pista = ""
            # Si no es correcto, generar pista
            arrow = ""
            if not correcto:
                val = parse_number(valor)
                esp = parse_number(esperado)
                if val is not None and esp is not None:
                    if val < esp:
                        pista = "Más alto"
                        arrow = "🔺"
                    elif val > esp:
                        pista = "Más bajo"
                        arrow = "🔻"
                else:
                    pista = "Incorrecto"
                    arrow = "❌"

            attempt['feedback'].append({
                'atributo': atributo,
                'valor': valor,
                'correcto': correcto,
                'pista': pista if not correcto else "",
                'arrow': arrow if not correcto else ""
            })

        formatted_attempts.append(attempt)

    return render(request, 'games/play.html', {
        'game': game,
        'target': target,
        'attempts': formatted_attempts,
        'won': won,
        'guess_error': guess_error,
    })
