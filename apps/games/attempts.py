# apps/games/attempts.py
"""
Construcción de intentos y feedback para la plantilla.
"""
from typing import Any, Dict, List, Set

from .models import Game, GameItem
from .utils import parse_to_float, numeric_feedback, to_list

__all__ = ["build_attempts"]


def _to_lower_set(value) -> Set[str]:
    """Convierte un valor (str | lista | None) en un set en minúsculas."""
    return {str(v).lower() for v in to_list(value)}


def _cross_group_partial(
    attr: str,
    grouped_attrs: Set[str],
    guess_set: Set[str],
    target_data: dict,
    defaults: dict,
) -> bool:
    """
    Devuelve True si el valor del atributo `attr` aparece
    en cualquier otro atributo del mismo grupo.
    """
    if attr not in grouped_attrs:
        return False

    target_group_values = {
        v.lower()
        for g_attr in grouped_attrs
        for v in to_list(target_data.get(g_attr) or defaults.get(g_attr))
    }
    return bool(guess_set & target_group_values)


# ──────────────────────────── Main ───────────────────────────────
def build_attempts(
    game: Game,
    guesses: List[GameItem],
    target: GameItem,
) -> List[Dict[str, Any]]:
    attempts: List[Dict[str, Any]] = []

    numeric_fields   = set(game.numeric_fields or [])
    grouped_attrs    = set(game.grouped_attributes or [])   # p.e. {"tipo1", "tipo2"}
    target_data      = target.data

    for item in guesses:
        attempt: Dict[str, Any] = {
            "name":  item.name,
            "is_correct": item.name == target.name,
            "feedback": [],
            "icon": getattr(item, "icon", None),
            "guess_image_url": item.get_image_url(),
        }

        for attr in game.attributes:
            guess_val   = item.data.get(attr)   or game.defaults.get(attr)
            target_val  = target_data.get(attr) or game.defaults.get(attr)

            is_match = partial = False
            fb = {"arrow": "", "hint": ""}

            # ───────────── Campos numéricos ─────────────
            if attr in numeric_fields:
                g_num = parse_to_float(guess_val)
                t_num = parse_to_float(target_val)
                is_match = g_num == t_num
                if not is_match:
                    fb = numeric_feedback(g_num, t_num)

            # ───────────── Campos texto / lista ─────────
            else:
                guess_set  = _to_lower_set(guess_val)
                target_set = _to_lower_set(target_val)

                if guess_set and target_set:
                    is_match = guess_set == target_set
                    partial  = not is_match and bool(guess_set & target_set)
                else:
                    is_match = guess_val == target_val

                # Coincidencia cruzada dentro del grupo (tipo1/tipo2)
                if not is_match and not partial:
                    partial = _cross_group_partial(
                        attr, grouped_attrs, guess_set, target_data, game.defaults
                    )

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