from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import GameElo
from apps.games.models import (
    DailyTarget,
    ExtraDailyPlay,
    Game,
    GameAttempt,
    GameItem,
    GameMode,
    GameModePlayType,
    PlaySession,
    PlaySessionType,
)
from apps.games.services.extra.start_extra_helpers import resolve_extra_mode


class ResolveExtraModeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mode_resolver", password="pass")
        self.game = Game.objects.create(name="Pokemon", slug="pokemon-extra-mode")
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="normal",
            label="Normal",
            play_type=GameModePlayType.WORDLE,
        )

    def test_resolve_extra_mode_uses_latest_extra_when_mode_slug_missing(self):
        ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            target=GameItem.objects.create(game=self.game, name="Pikachu"),
            bet_amount=20,
            completed=True,
        )

        resolved = resolve_extra_mode(self.game, self.user, None)

        self.assertEqual(resolved, self.mode)

    def test_resolve_extra_mode_uses_resolved_daily_when_no_extra_today(self):
        target = GameItem.objects.create(game=self.game, name="Pikachu")
        daily_target = DailyTarget.objects.create(
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            target=target,
            is_team=False,
        )
        daily_session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            session_type=PlaySessionType.DAILY,
            reference_id=daily_target.id,
        )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=target,
            is_correct=True,
            session=daily_session,
        )

        resolved = resolve_extra_mode(self.game, self.user, None)

        self.assertEqual(resolved, self.mode)


class StartExtraDailyViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="extra_player", password="pass")
        self.client = Client()
        self.client.force_login(self.user)
        self.game = Game.objects.create(name="Pokemon", slug="pokemon-extra-start")
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="normal",
            label="Normal",
            play_type=GameModePlayType.WORDLE,
        )
        self.target = GameItem.objects.create(game=self.game, name="Pikachu")
        GameElo.objects.create(user=self.user, game=self.game, mode=self.mode, elo=200)

        daily_target = DailyTarget.objects.create(
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            target=self.target,
            is_team=False,
        )
        daily_session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            session_type=PlaySessionType.DAILY,
            reference_id=daily_target.id,
        )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=self.target,
            is_correct=True,
            session=daily_session,
        )

        self.first_extra = ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            target=self.target,
            bet_amount=50,
            completed=True,
        )

    def test_start_second_extra_without_mode_slug_returns_play_extra_redirect(self):
        url = reverse("start_extra_daily", args=[self.game.slug])
        response = self.client.post(
            url,
            {"bet": 30, "return_extra_id": self.first_extra.id},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "ok")
        self.assertIn("/play-extra/", data["redirect_url"])

        second_extra = ExtraDailyPlay.objects.filter(user=self.user, game=self.game).latest("created_at")
        self.assertNotEqual(second_extra.id, self.first_extra.id)
        self.assertEqual(second_extra.mode, self.mode)
        self.assertEqual(second_extra.bet_amount, 30)

    def test_start_extra_without_enough_points_returns_ajax_error(self):
        GameElo.objects.filter(user=self.user, game=self.game, mode=self.mode).update(elo=10)
        url = reverse("start_extra_daily_mode", args=[self.game.slug, self.mode.slug])
        response = self.client.post(
            url,
            {"bet": 50, "return_extra_id": self.first_extra.id},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["status"], "error")
        self.assertIn("No tienes puntos suficientes", data["message"])

    def test_start_extra_without_enough_points_redirects_back_with_message(self):
        GameElo.objects.filter(user=self.user, game=self.game, mode=self.mode).update(elo=10)
        url = reverse("start_extra_daily_mode", args=[self.game.slug, self.mode.slug])
        response = self.client.post(
            url,
            {"bet": 50, "return_extra_id": self.first_extra.id},
            follow=True,
        )

        self.assertContains(response, "No tienes puntos suficientes en este juego para esa apuesta.")

    def test_play_extra_daily_includes_start_extra_url_with_mode(self):
        url = reverse("play_extra_daily", args=[self.first_extra.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        expected_start_url = reverse(
            "start_extra_daily_mode",
            args=[self.game.slug, self.mode.slug],
        )
        self.assertContains(response, f'data-start-extra-url="{expected_start_url}"')
