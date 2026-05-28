from typing import Any

from apps.games.services.catalog.attempt_feedback import AttributeFeedbackEvaluator
from apps.games.models import Game, GameItem

__all__ = ["build_attempts", "build_attempt_row"]


def build_attempt_row(game: Game, item: GameItem, target: GameItem) -> dict[str, Any]:
    attempt: dict[str, Any] = {
        "name": item.name,
        "is_correct": item.name == target.name,
        "feedback": [],
        "icon": getattr(item, "icon", None),
        "guess_image_url": item.get_image_url(),
    }

    evaluator = AttributeFeedbackEvaluator(game, target.data)
    for attribute in game.attributes:
        guess_value = item.data.get(attribute) or game.defaults.get(attribute)
        target_value = target.data.get(attribute) or game.defaults.get(attribute)
        result = evaluator.evaluate(attribute, guess_value, target_value)

        attempt["feedback"].append(
            {
                "attribute": attribute,
                "value": guess_value,
                "correct": result["is_match"],
                "partial": result["is_partial"],
                "hint": result["feedback_data"]["hint"],
                "arrow": result["feedback_data"]["arrow"],
            }
        )

    return attempt


def build_attempts(game: Game, guesses: list[GameItem], target: GameItem) -> list[dict[str, Any]]:
    return [build_attempt_row(game, item, target) for item in guesses]
