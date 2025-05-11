import random
import re
from typing import Any, Dict, List, Optional

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from apps.games.models import Game, GameItem


# ----------------------------------------------------------------------------
# Utils
# ----------------------------------------------------------------------------

def parse_number(value: Any) -> Optional[float]:
    """Try to convert *value* to a float.

    Removes any non‑numeric symbol except decimal separators ("," and ".") and
    the minus sign. If multiple dots are present we assume they are thousands
    separators and strip them. If the cleaned string still can’t be converted it
    returns ``None``.
    """
    cleaned: str = re.sub(r"[^\d.,\-]", "", str(value))
    if not cleaned:
        return None

    # Normalise decimal/thousand separators
    if cleaned.count(",") == 1 and cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif cleaned.count(".") > 1:
        cleaned = cleaned.replace(".", "")

    try:
        return float(cleaned)
    except ValueError:
        return None


def numeric_feedback(val: Optional[float], exp: Optional[float]) -> Dict[str, str]:
    """Return tuple (arrow, hint) comparing *val* against *exp*.

    ``exp`` *could* be None in the database. Design choice: we treat it as 0 so
    that the game keeps working and behaves just like the original implementation.
    """
    # Guard‑clause: both values must be valid numbers to give directional hints.
    if val is None or exp is None:
        return {"arrow": "❌", "hint": "Incorrecto"}

    if val == exp:
        return {"arrow": "", "hint": ""}
    if val < exp:
        return {"arrow": "🔺", "hint": "Más alto"}
    return {"arrow": "🔻", "hint": "Más bajo"}


# ----------------------------------------------------------------------------
# Helpers for the view (keep logic out of the main handler)
# ----------------------------------------------------------------------------

def _reset_session(session, game: Game) -> GameItem:
    """Initialise the session for a new game."""
    target = random.choice(list(game.items.all()))
    session.update({
        "target_id": target.id,
        "target_game": game.id,
        "guesses": [],
        "won": False,
    })
    # Return the selected target so the caller does not query again.
    return target


def _ordered_items(ids: List[int]) -> List[GameItem]:
    """Return GameItem queryset ordered as they appear in *ids* (latest on top)."""
    items = list(GameItem.objects.filter(id__in=ids))
    return sorted(items, key=lambda x: ids.index(x.id), reverse=True)


def _build_attempts(game: Game, guesses: List[GameItem], target: GameItem) -> List[Dict[str, Any]]:
    """Compose the structure expected by the template from *guesses*."""
    attempts: List[Dict[str, Any]] = []
    for item in guesses:
        attempt = {
            "name": item.name,
            "es_objetivo": item.name == target.name,
            "feedback": [],
        }

        for atributo in game.attributes:
            valor = item.data.get(atributo)
            esperado = target.data.get(atributo)

            val_num = parse_number(valor)
            exp_num = parse_number(esperado) or 0  # Same trick as the original code

            correcto = (val_num == exp_num) if (val_num is not None and exp_num is not None) else valor == esperado

            fb = numeric_feedback(val_num, exp_num) if not correcto else {"arrow": "", "hint": ""}

            attempt["feedback"].append({
                "atributo": atributo,
                "valor": valor,
                "correcto": correcto,
                "pista": fb["hint"],
                "arrow": fb["arrow"],
            })

        attempts.append(attempt)

    return attempts


def _handle_post(request, game: Game, target: GameItem) -> Optional[str]:
    """Process a POST request and mutate the session accordingly.

    Returns a redirect *slug* if we should short‑circuit the view afterwards.
    """
    session = request.session
    won = session.get("won", False)
    if won:
        return "play"  # User has already won; don’t process more guesses.

    guess_name: str = request.POST.get("guess", "").strip()
    guess_item: Optional[GameItem] = game.items.filter(name__iexact=guess_name).first()

    guesses_ids: List[int] = session.get("guesses", [])

    if not guess_item or guess_item.id in guesses_ids:
        session["guess_error"] = True
    else:
        guesses_ids.append(guess_item.id)
        session["guesses"] = guesses_ids

        if guess_item.name == target.name:
            session["won"] = True

    # After mutating state we always redirect to avoid POST‑redirect‑GET problems.
    return "play"


# ----------------------------------------------------------------------------
# Main view
# ----------------------------------------------------------------------------

@csrf_protect
def play_view(request, slug):
    game: Game = get_object_or_404(Game, slug=slug)
    session = request.session

    # ---------------------------------------------------------------------
    # Session bootstrap
    # ---------------------------------------------------------------------
    target: GameItem
    if session.get("target_id") and session.get("target_game") == game.id:
        target = GameItem.objects.get(id=session["target_id"])
    else:
        target = _reset_session(session, game)

    guesses_ids: List[int] = session.get("guesses", [])
    previous_guesses: List[GameItem] = _ordered_items(guesses_ids)
    won: bool = session.get("won", False)

    # ---------------------------------------------------------------------
    # POST handling — always redirect afterwards (Post/Redirect/Get)
    # ---------------------------------------------------------------------
    if request.method == "POST":
        slug_name = _handle_post(request, game, target)
        return redirect(slug_name, slug=slug)

    # ---------------------------------------------------------------------
    # Context for GET
    # ---------------------------------------------------------------------
    attempts = _build_attempts(game, previous_guesses, target)
    guess_error = session.pop("guess_error", False)

    return render(
        request,
        "games/play.html",
        {
            "game": game,
            "target": target,
            "attempts": attempts,
            "previous_guesses": previous_guesses,
            "won": won,
            "guess_error": guess_error,
        },
    )
