from typing import Any

from apps.games.utils import numeric_feedback, parse_to_float, to_list


def to_lower_set(value) -> set[str]:
    return {str(item).lower() for item in to_list(value)}


def is_grouped_partial_match(
    attribute: str,
    grouped_attributes: set[str],
    guess_set: set[str],
    target_data: dict,
    defaults: dict,
) -> bool:
    if attribute not in grouped_attributes:
        return False

    target_group_values = {
        value.lower()
        for group_attribute in grouped_attributes
        for value in to_list(target_data.get(group_attribute) or defaults.get(group_attribute))
    }
    return bool(guess_set & target_group_values)


class AttributeFeedbackEvaluator:

    def __init__(self, game, target_data: dict):
        self.numeric_fields = set(game.numeric_fields or [])
        self.grouped_attributes = set(game.grouped_attributes or [])
        self.defaults = game.defaults
        self.target_data = target_data

    def evaluate(self, attribute: str, guess_value, target_value) -> dict[str, Any]:
        if attribute in self.numeric_fields:
            return self._evaluate_numeric(guess_value, target_value)

        return self._evaluate_categorical(attribute, guess_value, target_value)

    def _evaluate_numeric(self, guess_value, target_value) -> dict[str, Any]:
        guess_numeric = parse_to_float(guess_value)
        target_numeric = parse_to_float(target_value)
        is_match = guess_numeric == target_numeric
        feedback_data = numeric_feedback(guess_numeric, target_numeric) if not is_match else {"arrow": "", "hint": ""}

        return {
            "is_match": is_match,
            "is_partial": False,
            "feedback_data": feedback_data,
        }

    def _evaluate_categorical(self, attribute: str, guess_value, target_value) -> dict[str, Any]:
        guess_set = to_lower_set(guess_value)
        target_set = to_lower_set(target_value)

        if guess_set and target_set:
            is_match = guess_set == target_set
            is_partial = not is_match and bool(guess_set & target_set)
        else:
            is_match = guess_value == target_value
            is_partial = False

        if not is_match and not is_partial:
            is_partial = is_grouped_partial_match(
                attribute,
                self.grouped_attributes,
                guess_set,
                self.target_data,
                self.defaults,
            )

        return {
            "is_match": is_match,
            "is_partial": is_partial,
            "feedback_data": {"arrow": "", "hint": ""},
        }
