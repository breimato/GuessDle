import random
import re
from typing import Any, Dict, List, Optional

from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_protect

from apps.games.models import Game, GameItem


# ------------------------------------------------------------------------------
# Utils
# ------------------------------------------------------------------------------

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


def numeric_feedback(guess_val: Optional[float], target_val: Optional[float]) -> Dict[str, str]:
    """
    Returns feedback for numeric comparison between guess and target values.
    Provides an arrow and a textual hint.
    If values can't be compared numerically, returns 'Incorrect'.
    """
    if guess_val is None or target_val is None:
        return {"arrow": "❌", "hint": "Incorrecto"}

    if guess_val == target_val:
        return {"arrow": "", "hint": ""}

    if guess_val < target_val:
        return {"arrow": "🔺", "hint": "Más"}
    return {"arrow": "🔻", "hint": "Menos"}


# ------------------------------------------------------------------------------
# Game logic helpers
# ------------------------------------------------------------------------------

def reset_game_session(session, game: Game) -> GameItem:
    """
    Initializes session state for a new game.
    Selects a random target and stores game metadata in session.
    """
    target = random.choice(list(game.items.all()))
    session.update({
        "target_id": target.id,
        "target_game": game.id,
        "guesses": [],
        "won": False,
    })
    return target


def order_items_by_guess(ids: List[int]) -> List[GameItem]:
    """
    Given a list of GameItem IDs, returns them sorted in reverse order
    (latest guesses first).
    """
    items = list(GameItem.objects.filter(id__in=ids))
    return sorted(items, key=lambda x: ids.index(x.id), reverse=True)


def build_attempts(game: Game, guesses: List[GameItem], target: GameItem) -> List[Dict[str, Any]]:
    """
    Builds structured feedback for each guess attempt, comparing attributes
    against the target item.
    Returns a list of dictionaries to be consumed by the template.
    """
    attempts: List[Dict[str, Any]] = []
    numeric_fields = set(game.numeric_fields or [])

    for item in guesses:
        attempt_data = {
            "name": item.name,
            "is_correct": item.name == target.name,
            "feedback": [],
        }

        for attr in game.attributes:
            guess_val = item.data.get(attr)
            target_val = target.data.get(attr)

            if attr in numeric_fields:
                guess_num = parse_to_float(guess_val) or 0
                target_num = parse_to_float(target_val) or 0
                is_match = guess_num == target_num
                fb = numeric_feedback(guess_num, target_num) if not is_match else {"arrow": "", "hint": ""}
            else:
                is_match = guess_val == target_val
                fb = {"arrow": "❌", "hint": ""} if not is_match else {"arrow": "", "hint": ""}

            attempt_data["feedback"].append({
                "attribute": attr,
                "value": guess_val or "—",
                "correct": is_match,
                "hint": fb["hint"],
                "arrow": fb["arrow"],
            })

        attempts.append(attempt_data)

    return attempts


def handle_post_guess(request, game: Game, target: GameItem) -> Optional[str]:
    """
    Handles a POST request with a guess submission:
    - Validates and records the guess.
    - Updates session with new guess or win status.
    Always returns a redirect name (to trigger PRG pattern).
    """
    session = request.session
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


# ------------------------------------------------------------------------------
# Main view
# ------------------------------------------------------------------------------

@csrf_protect
def play_view(request, slug):
    """
    View handler for the game play page.
    - Manages session setup
    - Handles guess POST submissions
    - Renders feedback and game state
    """
    game = get_object_or_404(Game, slug=slug)
    session = request.session

    if session.get("target_id") and session.get("target_game") == game.id:
        target = GameItem.objects.get(id=session["target_id"])
    else:
        target = reset_game_session(session, game)

    guess_ids: List[int] = session.get("guesses", [])
    previous_guesses: List[GameItem] = order_items_by_guess(guess_ids)
    has_won: bool = session.get("won", False)

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
