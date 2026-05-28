from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from apps.games.models import DailyTarget, Game, GameItem


class GuessEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="player", password="pass")
        self.game = Game.objects.create(name="LoL", slug="lol", attributes=["role"])
        self.target = GameItem.objects.create(game=self.game, name="Ahri", data={"role": "mage"})
        self.daily = DailyTarget.objects.create(
            game=self.game,
            target=self.target,
            date="2026-05-28",
            is_team=False,
        )
        self.client.force_login(self.user)

    def test_process_daily_guess_when_no_target_then_returns_400(self):
        empty_game = Game.objects.create(name="Empty", slug="empty", attributes=["role"])
        response = self.client.post(reverse("ajax_guess", args=[empty_game.slug]), {"guess": "Ahri"})

        self.assertEqual(response.status_code, 400)
