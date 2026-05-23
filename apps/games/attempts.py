"""Construction of attempts and feedback details for rendering in game templates."""

from typing import Any, Dict, List, Set

from .models import Game, GameItem
from .utils import parse_to_float, numeric_feedback, to_list

__all__ = ["build_attempts"]


def _to_lower_set(value) -> Set[str]:
    """Convert a value (string, list, or None) into a set of lowercase strings."""

    return {str(item).lower() for item in to_list(value)}


def _cross_group_partial(
    attribute: str,
    grouped_attributes: Set[str],
    guess_set: Set[str],
    target_data: dict,
    defaults: dict,
) -> bool:
    """Determine if the attribute value matches any other attribute in the same group."""

    if attribute not in grouped_attributes:
        return False

    target_group_values = {
        value.lower()
        for group_attribute in grouped_attributes
        for value in to_list(target_data.get(group_attribute) or defaults.get(group_attribute))
    }
    return bool(guess_set & target_group_values)


def build_attempts(
    game: Game,
    guesses: List[GameItem],
    target: GameItem,
) -> List[Dict[str, Any]]:
    """Build a list of user attempts with attribute-by-attribute feedback matching the target item."""

    attempts: List[Dict[str, Any]] = []

    numeric_fields = set(game.numeric_fields or [])
    grouped_attributes = set(game.grouped_attributes or [])
    target_data = target.data

    for item in guesses:
        attempt: Dict[str, Any] = {
            "name": item.name,
            "is_correct": item.name == target.name,
            "feedback": [],
            "icon": getattr(item, "icon", None),
            "guess_image_url": item.get_image_url(),
        }

        for attribute in game.attributes:
            guess_value = item.data.get(attribute) or game.defaults.get(attribute)
            target_value = target_data.get(attribute) or game.defaults.get(attribute)

            is_match = False
            is_partial = False
            feedback_data = {"arrow": "", "hint": ""}

            if attribute in numeric_fields:
                guess_numeric = parse_to_float(guess_value)
                target_numeric = parse_to_float(target_value)
                is_match = guess_numeric == target_numeric
                if not is_match:
                    feedback_data = numeric_feedback(guess_numeric, target_numeric)
            else:
                guess_set = _to_lower_set(guess_value)
                target_set = _to_lower_set(target_value)

                if guess_set and target_set:
                    is_match = guess_set == target_set
                    is_partial = not is_match and bool(guess_set & target_set)
                else:
                    is_match = guess_value == target_value

                if not is_match and not is_partial:
                    is_partial = _cross_group_partial(
                        attribute, grouped_attributes, guess_set, target_data, game.defaults
                    )

            attempt["feedback"].append(
                {
                    "attribute": attribute,
                    "value": guess_value,
                    "correct": is_match,
                    "partial": is_partial,
                    "hint": feedback_data["hint"],
                    "arrow": feedback_data["arrow"],
                }
            )

        attempts.append(attempt)

    return attempts