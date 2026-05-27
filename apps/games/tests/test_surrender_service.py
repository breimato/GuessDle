from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.games.models import DailyTarget, Game, GameItem, PlaySession, PlaySessionType
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.games.services.gameplay.surrender import SurrenderService

User = get_user_model()


class SurrenderServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="player", password="secret")
        self.game = Game.objects.create(
            name="Test Game",
            slug="test-game",
            attributes=["region"],
        )
        self.target_item = GameItem.objects.create(game=self.game, name="Target Hero")
        self.daily_target = DailyTarget.objects.create(
            game=self.game,
            target=self.target_item,
            date="2026-05-26",
            is_team=False,
        )

    def test_daily_surrender_marks_session_and_returns_target_name(self):
        surrender_result = SurrenderService(self.game, self.user).process(
            daily_target=self.daily_target,
        )

        play_session = PlaySession.objects.get(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=self.daily_target.id,
        )

        self.assertTrue(play_session.surrendered)
        self.assertEqual(surrender_result.target_name, "Target Hero")

    def test_daily_surrender_rejects_second_attempt(self):
        SurrenderService(self.game, self.user).process(daily_target=self.daily_target)

        with self.assertRaisesMessage(ValueError, "Ya te has rendido en esta partida."):
            SurrenderService(self.game, self.user).process(daily_target=self.daily_target)

    def test_daily_surrender_rejects_after_win(self):
        play_session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            daily_target=self.daily_target,
        )
        play_session.surrendered = False
        play_session.save(update_fields=["surrendered"])

        from apps.games.models import GameAttempt

        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            session=play_session,
            guess=self.target_item,
            is_correct=True,
        )

        with self.assertRaisesMessage(ValueError, "Ya has ganado esta partida."):
            SurrenderService(self.game, self.user).process(daily_target=self.daily_target)
