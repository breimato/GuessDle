from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.games.models import Game, GameMode, GameModePlayType
from apps.games.services.catalog.mode_select_service import ModeSelectService


class ModeSelectServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="nav_user", password="pass")
        self.game = Game.objects.create(
            name="Nav Game",
            slug="nav-game",
            data_source_url="https://example.com",
            attributes=["id"],
        )
        self.normal = GameMode.objects.create(
            game=self.game,
            slug="normal",
            label="Normal",
            play_type=GameModePlayType.WORDLE,
            sort_order=0,
        )
        self.hard = GameMode.objects.create(
            game=self.game,
            slug="dificil",
            label="Dificil",
            play_type=GameModePlayType.WORDLE,
            sort_order=1,
        )
        self.proximity = GameMode.objects.create(
            game=self.game,
            slug="proximidad",
            label="Proximidad",
            play_type=GameModePlayType.PROXIMITY,
            sort_order=2,
        )

    def test_next_playable_entry_follows_sort_order(self):
        service = ModeSelectService(self.game, self.user)
        next_entry = service.next_playable_entry(self.normal)
        self.assertEqual(next_entry["mode"].slug, "dificil")
        self.assertEqual(
            next_entry["play_url"],
            reverse("play_mode", args=[self.game.slug, "dificil"]),
        )

    def test_last_playable_mode_has_no_next(self):
        service = ModeSelectService(self.game, self.user)
        self.assertIsNone(service.next_playable_entry(self.hard))
