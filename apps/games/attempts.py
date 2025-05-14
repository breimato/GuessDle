# apps/games/attempts.py
"""
Construcción de intentos y feedback para la plantilla.
"""
from typing import Any, Dict, List

from .models import Game, GameItem
from .utils import parse_to_float, numeric_feedback, to_list

__all__ = ["build_attempts"]


def build_attempts(game: Game, guesses: List[GameItem], target: GameItem) -> List[Dict[str, Any]]:
    attempts: List[Dict[str, Any]] = []
    numeric_fields = set(game.numeric_fields or [])
    tgt_data = target.data

    for item in guesses:
        attempt = {
            "name": item.name,
            "is_correct": item.name == target.name,
            "feedback": [],
            "icon": getattr(item, "icon", None),
        }

        for attr in game.attributes:
            guess_val = item.data.get(attr) or game.defaults.get(attr)
            target_val = tgt_data.get(attr) or game.defaults.get(attr)

            is_match = partial = False
            fb = {"arrow": "", "hint": ""}

            # Numéricos
            if attr in numeric_fields:
                g_num = parse_to_float(guess_val)
                t_num = parse_to_float(target_val)
                is_match = g_num == t_num
                if not is_match:
                    fb = numeric_feedback(g_num, t_num)
            # Texto / multi-valor
            else:
                guess_set = set(map(str.lower, to_list(guess_val)))
                target_set = set(map(str.lower, to_list(target_val)))
                if guess_set and target_set:
                    is_match = guess_set == target_set
                    partial = not is_match and bool(guess_set & target_set)
                else:
                    is_match = guess_val == target_val

            attempt["feedback"].append(
                {
                    "attribute": attr,
                    "value": guess_val,
                    "correct": is_match,
                    "partial": partial,
                    "hint": fb["hint"],
                    "arrow": fb["arrow"],
                }
            )
        attempts.append(attempt)
    return attempts
