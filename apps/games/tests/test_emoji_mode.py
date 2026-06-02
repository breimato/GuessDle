from datetime import date
import json
from pathlib import Path

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import GameElo
from apps.games.models import (
    DailyTarget,
    EmojiClueSet,
    Game,
    GameItem,
    GameMode,
    GameModePlayType,
    PlaySession,
)
from apps.games.services.catalog.item_pool_service import ItemPoolService
from apps.games.services.emoji.daily_target_service import EmojiDailyTargetService
from apps.games.services.emoji.clue_importer import import_emoji_clues
from apps.games.services.emoji.clue_validator import EmojiClueImportError, validate_emoji_clue_payload
from apps.games.services.emoji.clue_service import EmojiClueService
from apps.games.services.emoji.guess_processor import EmojiGuessProcessor
from apps.games.services.play_session.outcome_registry import resolve_outcome
from apps.games.services.play_session.play_context import PlayContext


class EmojiClueBankFileTests(TestCase):
    def test_lol_emoji_clues_json_covers_full_roster(self):
        root = Path(__file__).resolve().parents[3]
        roster = json.loads((root / "league-of-legends.json").read_text(encoding="utf-8"))
        payload = json.loads((root / "data" / "lol" / "emoji_clues.json").read_text(encoding="utf-8"))

        validate_emoji_clue_payload(payload)

        roster_names = [entry["name"] for entry in roster]
        payload_names = [entry["item_name"] for entry in payload]
        self.assertEqual(payload_names, roster_names)
        self.assertEqual(len(payload), 172)

        ahri = next(entry for entry in payload if entry["item_name"] == "Ahri")
        self.assertEqual(ahri["clues"], ["🦊", "❤️", "🐾", "🥵"])

        yasuo = next(entry for entry in payload if entry["item_name"] == "Yasuo")
        self.assertEqual(yasuo["clues"], ["🌪️", "🧱", "💨", "⚔️"])


class EmojiClueImportTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="LoL Emoji Import",
            slug="lol-emoji-import",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.item = GameItem.objects.create(
            game=self.game,
            name="Ahri",
            data={"role": "Mage"},
        )

    def test_import_creates_clue_set(self):
        created = import_emoji_clues(
            self.game,
            [{"item_name": "Ahri", "clues": ["🦊", "💫", "🔮"]}],
        )
        self.assertEqual(created, 1)
        clue_set = EmojiClueSet.objects.get(game=self.game, item=self.item)
        self.assertEqual(clue_set.clues, ["🦊", "💫", "🔮"])

    def test_import_rejects_too_few_clues(self):
        with self.assertRaises(EmojiClueImportError):
            import_emoji_clues(
                self.game,
                [{"item_name": "Ahri", "clues": ["🦊", "💫"]}],
            )


class EmojiGuessProcessorTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emoji_player", password="pass")
        self.game = Game.objects.create(
            name="LoL Emoji Play",
            slug="lol-emoji-play",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="emojis",
            label="Emojis",
            play_type=GameModePlayType.EMOJI,
        )
        self.target = GameItem.objects.create(game=self.game, name="Ahri", data={"role": "Mage"})
        self.other = GameItem.objects.create(game=self.game, name="Lux", data={"role": "Mage"})
        EmojiClueSet.objects.create(
            game=self.game,
            item=self.target,
            clues=["🦊", "💫", "🔮", "🏃‍♀️"],
        )
        self.daily_target = DailyTarget.objects.create(
            game=self.game,
            mode=self.mode,
            date=date.today(),
            is_team=False,
            target=self.target,
        )

    def _processor(self):
        return EmojiGuessProcessor(self.game, self.mode, self.user)

    def _post(self, name: str):
        class Request:
            POST = {"guess": name}

        return Request()

    def test_wrong_guess_reveals_next_clue(self):
        processor = self._processor()
        is_valid, state = processor.process(self._post("Lux"), self.daily_target)
        self.assertTrue(is_valid)
        self.assertFalse(state["won"])
        self.assertEqual(state["revealed_clues"], ["🦊", "💫"])
        self.assertEqual(len(state["attempts"]), 1)
        self.assertEqual(state["attempts"][0]["name"], "Lux")
        self.assertFalse(state["attempts"][0]["is_correct"])
        self.assertIn("guess_image_url", state["attempts"][0])
        session = PlaySession.objects.get(user=self.user, reference_id=self.daily_target.id)
        self.assertEqual(session.emoji_clues_revealed, 2)

    def test_clues_do_not_grow_beyond_max_after_many_wrong_guesses(self):
        processor = self._processor()
        wrong_names = ["Lux", "Yasuo", "Garen", "Darius", "Zed", "Akali"]
        for name in wrong_names:
            GameItem.objects.get_or_create(
                game=self.game,
                name=name,
                defaults={"data": {"role": "Fighter"}},
            )
            processor.process(self._post(name), self.daily_target)

        session = PlaySession.objects.get(user=self.user, reference_id=self.daily_target.id)
        self.assertEqual(session.emoji_clues_revealed, 4)
        GameItem.objects.get_or_create(
            game=self.game,
            name="Ekko",
            defaults={"data": {"role": "Assassin"}},
        )
        _, state = processor.process(self._post("Ekko"), self.daily_target)
        self.assertEqual(len(state["revealed_clues"]), 4)

    def test_correct_guess_does_not_award_elo(self):
        GameElo.objects.create(user=self.user, game=self.game, mode=self.mode, elo=100)
        processor = self._processor()
        is_valid, state = processor.process(self._post("Ahri"), self.daily_target)
        self.assertTrue(is_valid)
        self.assertTrue(state["won"])

        play_context = PlayContext.exactly_one(daily_target=self.daily_target)
        outcome = resolve_outcome(self.game, self.user, play_context)
        self.assertEqual(outcome["points_awarded"], 0)
        self.assertEqual(GameElo.objects.get(user=self.user, game=self.game, mode=self.mode).elo, 100)


class EmojiItemPoolTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="LoL Emoji Pool",
            slug="lol-emoji-pool",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="emojis",
            label="Emojis",
            play_type=GameModePlayType.EMOJI,
        )
        self.with_clues = GameItem.objects.create(game=self.game, name="Ahri", data={})
        self.without_clues = GameItem.objects.create(game=self.game, name="Lux", data={})
        EmojiClueSet.objects.create(
            game=self.game,
            item=self.with_clues,
            clues=["🦊", "💫", "🔮"],
        )

    def test_pick_random_with_emoji_clues_only_returns_configured_items(self):
        picked = ItemPoolService(self.game, self.mode).pick_random_with_emoji_clues()
        self.assertEqual(picked, self.with_clues)


class EmojiModeSelectTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="emoji_selector", password="pass")
        self.client.login(username="emoji_selector", password="pass")
        self.game = Game.objects.create(
            name="LoL Emoji Select",
            slug="lol-emoji-select",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        GameMode.objects.create(
            game=self.game,
            slug="normal",
            label="Diario",
            play_type=GameModePlayType.WORDLE,
            sort_order=0,
        )
        self.emoji_mode = GameMode.objects.create(
            game=self.game,
            slug="emojis",
            label="Emojis",
            play_type=GameModePlayType.EMOJI,
            sort_order=1,
        )
        target = GameItem.objects.create(game=self.game, name="Ahri", data={})
        EmojiClueSet.objects.create(
            game=self.game,
            item=target,
            clues=["🦊", "💫", "🔮"],
        )
        DailyTarget.objects.create(
            game=self.game,
            mode=self.emoji_mode,
            date=date.today(),
            is_team=False,
            target=target,
        )

    def test_mode_select_shows_emojis_without_extras(self):
        response = self.client.get(reverse("play", args=[self.game.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Emojis")
        self.assertNotContains(response, "Apostar y jugar extra")

    def test_mode_select_shows_unavailable_without_clue_bank(self):
        EmojiClueSet.objects.all().delete()
        response = self.client.get(reverse("play", args=[self.game.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No disponible")


class EmojiDailyTargetServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="emoji_daily", password="pass")
        self.game = Game.objects.create(
            name="LoL Emoji Daily",
            slug="lol-emoji-daily",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="emojis",
            label="Emojis",
            play_type=GameModePlayType.EMOJI,
        )
        self.item = GameItem.objects.create(game=self.game, name="Ahri", data={})
        EmojiClueSet.objects.create(
            game=self.game,
            item=self.item,
            clues=["🦊", "💫", "🔮"],
        )

    def test_resolve_playable_target_creates_today_target(self):
        service = EmojiDailyTargetService(self.game, self.user, self.mode)
        daily_target = service.resolve_playable_target()
        self.assertIsNotNone(daily_target)
        self.assertEqual(daily_target.target, self.item)
        self.assertEqual(daily_target.date, date.today())


class EmojiViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="emoji_viewer", password="pass")
        self.client.login(username="emoji_viewer", password="pass")
        self.game = Game.objects.create(
            name="LoL Emoji View",
            slug="lol-emoji-view",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="emojis",
            label="Emojis",
            play_type=GameModePlayType.EMOJI,
        )
        self.target = GameItem.objects.create(game=self.game, name="Ahri", data={})
        self.other = GameItem.objects.create(game=self.game, name="Lux", data={})
        EmojiClueSet.objects.create(
            game=self.game,
            item=self.target,
            clues=["🦊", "💫", "🔮"],
        )
        DailyTarget.objects.create(
            game=self.game,
            mode=self.mode,
            date=date.today(),
            is_team=False,
            target=self.target,
        )

    def test_play_page_renders_clues_and_guess_area(self):
        response = self.client.get(reverse("play_mode", args=[self.game.slug, self.mode.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "emoji-clues-display")
        self.assertContains(response, "emoji-guesses-list")
        self.assertContains(response, "🦊")

    def test_play_creates_daily_target_when_missing(self):
        DailyTarget.objects.filter(game=self.game, mode=self.mode).delete()
        response = self.client.get(reverse("play_mode", args=[self.game.slug, self.mode.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            DailyTarget.objects.filter(
                game=self.game,
                mode=self.mode,
                date=date.today(),
                is_team=False,
            ).exists()
        )

    def test_play_without_clue_bank_shows_unavailable_page(self):
        EmojiClueSet.objects.all().delete()
        response = self.client.get(reverse("play_mode", args=[self.game.slug, self.mode.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aún no hay pistas emoji configuradas")
        self.assertNotContains(response, "emoji-clues-display")

    def test_guess_endpoint_returns_next_clue_on_miss(self):
        url = reverse("emoji_guess", args=[self.game.slug, self.mode.slug])
        response = self.client.post(url, {"guess": "Lux"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["won"])
        self.assertEqual(payload["revealed_clues"], ["🦊", "💫"])
        self.assertEqual(len(payload["attempts"]), 1)
        self.assertEqual(payload["attempts"][0]["name"], "Lux")
        self.assertIn("guess_image_url", payload["attempts"][0])

    def test_play_page_renders_guess_cards_after_attempt(self):
        url = reverse("emoji_guess", args=[self.game.slug, self.mode.slug])
        self.client.post(url, {"guess": "Lux"})
        response = self.client.get(reverse("play_mode", args=[self.game.slug, self.mode.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "emoji-guess-card")
        self.assertContains(response, "emoji-guess-card__portrait")
        self.assertContains(response, "Emojis del día")
        self.assertContains(response, "emojis")

    def test_visible_clues_helper_starts_with_one(self):
        clues = EmojiClueService.get_clues(self.game, self.target)
        self.assertEqual(EmojiClueService.visible_clues(clues, 1), ["🦊"])
