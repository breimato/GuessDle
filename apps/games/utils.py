"""General helper functions for game data processing and numeric comparison feedback."""

import re
from typing import Any, List, Optional, Dict

__all__ = [
    "parse_to_float",
    "numeric_feedback",
    "to_list",
]


def parse_to_float(value: Any) -> Optional[float]:
    """Convert a numeric string containing European or American decimal separators to a float."""

    if value is None:
        return None

    match = re.search(r"[-+]?\d[\d.,]*", str(value))
    if not match:
        return None

    number_string = match.group()

    if number_string.count(".") > 1 and number_string.count(",") == 0:
        number_string = number_string.replace(".", "")
    elif number_string.count(",") > 1 and number_string.count(".") == 0:
        number_string = number_string.replace(",", "")
    elif "." in number_string and "," in number_string:
        if number_string.rfind(",") > number_string.rfind("."):
            number_string = number_string.replace(".", "").replace(",", ".")
        else:
            number_string = number_string.replace(",", "")
    elif "," in number_string:
        number_string = number_string.replace(",", ".")

    try:
        return float(number_string)
    except ValueError:
        return None


def numeric_feedback(guess: Optional[float], target: Optional[float]) -> Dict[str, str]:
    """Generate visual feedback (arrow direction and text hint) comparing a guess with the target value."""

    if guess is None or target is None:
        return {"arrow": "", "hint": "Incorrect"}
    if guess == target:
        return {"arrow": "", "hint": ""}
    return {
        "arrow": "▲" if guess < target else "▼",
        "hint": "Higher" if guess < target else "Lower",
    }


def to_list(raw_value: Any) -> List[str]:
    """Normalize multi-value field content or comma-separated string into a list of strings."""

    if raw_value is None:
        return []
    if isinstance(raw_value, (list, tuple)):
        return list(raw_value)
    return [item.strip() for item in str(raw_value).split(",") if item.strip()]
