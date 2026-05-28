from django.test import TestCase

from apps.games.models import Game, GameItem
from apps.games.services.catalog.attempt_feedback import AttributeFeedbackEvaluator


class AttributeFeedbackEvaluatorTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="Test",
            slug="test",
            attributes=["role", "power"],
            numeric_fields=["power"],
            defaults={"role": "unknown", "power": 0},
        )
        self.target = GameItem.objects.create(
            game=self.game,
            name="Target",
            data={"role": "mage", "power": 100},
        )

    def test_evaluate_numeric_when_equal_then_match(self):
        evaluator = AttributeFeedbackEvaluator(self.game, self.target.data)
        result = evaluator.evaluate("power", 100, 100)

        self.assertTrue(result["is_match"])
        self.assertFalse(result["is_partial"])

    def test_evaluate_categorical_when_same_set_then_match(self):
        evaluator = AttributeFeedbackEvaluator(self.game, self.target.data)
        result = evaluator.evaluate("role", "mage", "mage")

        self.assertTrue(result["is_match"])
