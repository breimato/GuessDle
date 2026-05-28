from django.contrib.auth.models import User
from django.test import TestCase

from apps.games.services.catalog.attempts import build_attempts
from apps.games.models import Game, GameItem, GameAttempt, PlaySession, PlaySessionType
from apps.games.services.hints.hint_reveal_service import HintRevealService, HINT_INTERVAL


class HintRevealServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="hintuser", password="pass")
        self.game = Game.objects.create(
            name="Test Game",
            slug="test-hint-game",
            attributes=["tipo_1", "tipo_2", "region"],
            hint_reveal_columns=["tipo_1", "tipo_2", "region"],
            data_source_url="http://example.com/data.json",
            json_file="",
        )
        self.target = GameItem.objects.create(
            game=self.game,
            name="Target",
            data={"tipo_1": "Fuego", "tipo_2": "Volador", "region": "Kanto"},
        )
        self.other = GameItem.objects.create(
            game=self.game,
            name="Other",
            data={"tipo_1": "Agua", "tipo_2": "Planta", "region": "Johto"},
        )
        self.partial_match = GameItem.objects.create(
            game=self.game,
            name="Partial",
            data={"tipo_1": "Fuego", "tipo_2": "Planta", "region": "Johto"},
        )
        self.session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=1,
        )

    def _add_attempt(self, item):
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            session=self.session,
            guess=item,
            is_correct=item.pk == self.target.pk,
        )

    def _service(self):
        return HintRevealService(self.session, self.game, self.target)

    def test_no_hints_when_columns_not_configured(self):
        self.game.hint_reveal_columns = []
        self.game.save()
        state = self._service().get_hint_state()
        self.assertFalse(state["enabled"])
        self.assertEqual(state["slots_pending"], 0)

    def test_slots_earned_every_five_attempts(self):
        for _ in range(4):
            self._add_attempt(self.other)
        state = self._service().get_hint_state()
        self.assertEqual(state["slots_earned"], 0)
        self.assertEqual(state["slots_pending"], 0)

        self._add_attempt(self.other)
        state = self._service().get_hint_state()
        self.assertEqual(state["slots_earned"], 1)
        self.assertEqual(state["slots_pending"], 1)

        for _ in range(HINT_INTERVAL):
            self._add_attempt(self.other)
        state = self._service().get_hint_state()
        self.assertEqual(state["slots_earned"], 2)
        self.assertEqual(state["slots_pending"], 2)

    def test_suggested_skips_known_column(self):
        for _ in range(5):
            self._add_attempt(self.partial_match)

        built = build_attempts(self.game, [self.partial_match], self.target)
        tipo1_correct = any(
            fb["attribute"] == "tipo_1" and fb["correct"]
            for fb in built[0]["feedback"]
        )
        self.assertTrue(tipo1_correct)

        state = self._service().get_hint_state()
        self.assertEqual(state["suggested_attribute"], "tipo_2")
        self.assertEqual(len(state["eligible_columns"]), 1)
        self.assertEqual(state["eligible_columns"][0]["attribute"], "tipo_2")

    def test_reveal_persists_and_consumes_slot(self):
        for _ in range(5):
            self._add_attempt(self.other)

        state = self._service().reveal("tipo_2")
        self.assertEqual(len(state["revealed_hints"]), 1)
        self.assertEqual(state["revealed_hints"][0]["attribute"], "tipo_2")
        self.assertEqual(state["revealed_hints"][0]["label"], "tipo 2")
        self.assertEqual(state["revealed_hints"][0]["value"], "Volador")
        self.assertEqual(state["slots_pending"], 0)

        self.session.refresh_from_db()
        self.assertEqual(len(self.session.revealed_hints), 1)

    def test_cannot_reveal_unknown_column(self):
        for _ in range(5):
            self._add_attempt(self.other)

        with self.assertRaises(ValueError):
            self._service().reveal("region_invalid")

    def test_cannot_reveal_without_pending_slot(self):
        with self.assertRaises(ValueError):
            self._service().reveal("tipo_1")

    def test_cannot_reveal_already_known_column(self):
        for _ in range(5):
            self._add_attempt(self.partial_match)

        with self.assertRaises(ValueError):
            self._service().reveal("tipo_1")
