import random
import re
from typing import Any, Dict, List, Optional

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from apps.games.models import Game, GameItem


# ----------------------------------------------------------------------
# Utils
# ----------------------------------------------------------------------

def parse_to_float(value: Any) -> Optional[float]:
    """
    Tries to convert a value into a float, handling various formatting cases:
    - Removes non-numeric characters except '.', ',', and '-'.
    - Normalizes thousands and decimal separators.
    Returns None if parsing fails.
    """
    cleaned = re.sub(r"[^\d.,\-]", "", str(value))
    if not cleaned:
        return None

    if cleaned.count(",") == 1 and cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def numeric_feedback(
    guess_val: Optional[float],
    target_val: Optional[float],
) -> Dict[str, str]:
    """
    Returns feedback for numeric comparison between guess and target values.
    """
    if guess_val is None or target_val is None:
        return {"arrow": "", "hint": "Incorrecto"}

    if guess_val == target_val:
        return {"arrow": "", "hint": ""}

    if guess_val < target_val:
        return {"arrow": "▲", "hint": "Más"}
    return {"arrow": "▼", "hint": "Menos"}


def to_list(raw: Any) -> List[str]:
    """
    Normaliza cualquier valor recibido de la BBDD a una lista de strings:
    - Si ya es lista/tupla → la devuelve como lista.
    - Si es None → lista vacía.
    - En cualquier otro caso → split por comas.
    """
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return list(raw)
    return [s.strip() for s in str(raw).split(",") if s.strip()]


# ----------------------------------------------------------------------
# Game logic helpers
# ----------------------------------------------------------------------

def reset_game_session(session, game: Game) -> GameItem:
    """Inicializa una nueva partida en sesión."""
    target = random.choice(list(game.items.all()))
    session.update(
        {
            "target_id": target.id,
            "target_game": game.id,
            "guesses": [],
            "won": False,
        }
    )
    return target


def order_items_by_guess(ids: List[int]) -> List[GameItem]:
    """Devuelve los GameItem en el mismo orden en que se adivinaron (último primero)."""
    items = list(GameItem.objects.filter(id__in=ids))
    return sorted(items, key=lambda x: ids.index(x.id), reverse=True)


def build_attempts(
    game: Game,
    guesses: List[GameItem],
    target: GameItem,
) -> List[Dict[str, Any]]:
    """
    Construye una lista con feedback estructurado para cada intento.
    Detecta:
      - acierto total (verde)
      - coincidencia parcial (amarillo)
      - error (rojo)
    """
    attempts: List[Dict[str, Any]] = []
    numeric_fields = set(game.numeric_fields or [])

    # Pre-computamos los datos del objetivo para no acceder al JSON una y otra vez
    target_data = target.data

    for item in guesses:
        attempt_data: Dict[str, Any] = {
            "name": item.name,
            "icon": getattr(item, "icon_url", None),  # <= o el campo que uses
            "is_correct": item.name == target.name,
            "feedback": [],
        }

        for attr in game.attributes:
            guess_val = item.data.get(attr)
            target_val = target_data.get(attr)

            is_match = False
            partial_match = False
            fb = {"arrow": "", "hint": ""}

            # --- numéricos --------------------------------------------------
            if attr in numeric_fields:
                guess_num = parse_to_float(guess_val) or 0
                target_num = parse_to_float(target_val) or 0

                is_match = guess_num == target_num
                if not is_match:
                    fb = numeric_feedback(guess_num, target_num)

            # --- multi-opción / strings con comas ---------------------------
            else:
                guess_tokens = to_list(guess_val)
                target_tokens = to_list(target_val)

                if guess_tokens and target_tokens:
                    guess_set = set(map(str.lower, map(str, guess_tokens)))
                    target_set = set(map(str.lower, map(str, target_tokens)))

                    is_match = guess_set == target_set
                    partial_match = not is_match and bool(guess_set & target_set)
                else:
                    # caso escalar sin listas ni comas
                    is_match = guess_val == target_val

            # ----------------------------------------------------------------
            attempt_data["feedback"].append(
                {
                    "attribute": attr,
                    "value": guess_val or "—",
                    "correct": is_match,
                    "partial": partial_match,
                    "hint": fb["hint"],
                    "arrow": fb["arrow"],
                }
            )

        attempts.append(attempt_data)

    return attempts


def handle_post_guess(request, game: Game, target: GameItem) -> str:
    """Procesa el POST con el intento de adivinar."""
    session = request.session

    # si ya ganó, solo recarga página (PRG pattern)
    if session.get("won", False):
        return "play"

    guess_name = request.POST.get("guess", "").strip()
    guess_item = game.items.filter(name__iexact=guess_name).first()

    guess_ids: List[int] = session.get("guesses", [])

    if not guess_item or guess_item.id in guess_ids:
        session["guess_error"] = True
    else:
        guess_ids.append(guess_item.id)
        session["guesses"] = guess_ids

        if guess_item.name == target.name:
            session["won"] = True

    return "play"


# ----------------------------------------------------------------------
# Main view
# ----------------------------------------------------------------------

@csrf_protect
def play_view(request, slug):
    """
    Vista principal de la partida.
    - Maneja la sesión y el objetivo.
    - Procesa los intentos POST.
    - Renderiza el estado del juego.
    """
    game = get_object_or_404(Game, slug=slug)
    session = request.session

    # recuperamos o inicializamos objetivo
    if session.get("target_id") and session.get("target_game") == game.id:
        target = GameItem.objects.get(id=session["target_id"])
    else:
        target = reset_game_session(session, game)

    # lista de objetos GameItem adivinados (orden inverso)
    guess_ids: List[int] = session.get("guesses", [])
    previous_guesses = order_items_by_guess(guess_ids)
    has_won: bool = session.get("won", False)

    # PRG: procesamos POST y redirigimos
    if request.method == "POST":
        redirect_to = handle_post_guess(request, game, target)
        return redirect(redirect_to, slug=slug)

    attempts = build_attempts(game, previous_guesses, target)
    guess_error = session.pop("guess_error", False)

    return render(
        request,
        "games/play.html",
        {
            "game": game,
            "target": target,
            "attempts": attempts,
            "previous_guesses": previous_guesses,
            "won": has_won,
            "guess_error": guess_error,
        },
    )
