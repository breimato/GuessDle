from django.contrib.auth.models import User
from django.test import TestCase

from apps.accounts.models import GameElo
from apps.accounts.services.wallet.score_service import ScoreService
from apps.games.models import ExtraDailyPlay, Game, GameAttempt, GameItem, PlaySession, PlaySessionType
from apps.games.services.extra.payout import compute_extra_bet_payout, evaluate_extra_bet_won, format_extra_bet_goal
from apps.games.services.extra.extra_daily_service import ExtraDailyService
from apps.games.services.play_session.play_session_service import PlaySessionService
from apps.games.services.play_session.result_updater import ResultUpdater


class ExtraBetPayoutTests(TestCase):
    def test_compute_extra_bet_payout_when_won_then_credits_stake_plus_half_profit(self):
        payout = compute_extra_bet_payout(100, True)

        self.assertEqual(payout.credit, 150)
        self.assertEqual(payout.net_profit, 50)
        self.assertEqual(payout.points_awarded, 50)

    def test_compute_extra_bet_payout_when_lost_then_no_credit(self):
        payout = compute_extra_bet_payout(100, False)

        self.assertEqual(payout.credit, 0)
        self.assertEqual(payout.net_profit, 0)
        self.assertEqual(payout.points_awarded, 0)


class ResultUpdaterExtraBetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="better", password="pass")
        self.game = Game.objects.create(name="LoL", slug="lol")
        self.target = GameItem.objects.create(game=self.game, name="Ahri")
        GameElo.objects.create(user=self.user, game=self.game, elo=100)

    def test_extra_bet_when_won_then_balance_is_stake_plus_half_profit(self):
        prior_session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=1,
        )
        wrong_guess = GameItem.objects.create(game=self.game, name="Wrong")
        for _ in range(4):
            GameAttempt.objects.create(
                user=self.user,
                game=self.game,
                guess=wrong_guess,
                is_correct=False,
                session=prior_session,
            )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=self.target,
            is_correct=True,
            session=prior_session,
        )

        extra_play = ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            target=self.target,
            bet_amount=100,
        )
        GameElo.objects.filter(user=self.user, game=self.game).update(elo=0)

        session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            extra_play=extra_play,
        )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=self.target,
            is_correct=True,
            session=session,
        )

        result = ResultUpdater(self.game, self.user).update_for_game(extra_play=extra_play)

        self.assertTrue(result["bet_won"])
        self.assertEqual(result["net_profit"], 50)
        self.assertEqual(ScoreService(self.user, self.game).score_obj.elo, 150)

    def test_extra_bet_when_over_average_without_win_then_marks_completed(self):
        prior_session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=99,
        )
        wrong_guess = GameItem.objects.create(game=self.game, name="Miss")
        for _ in range(4):
            GameAttempt.objects.create(
                user=self.user,
                game=self.game,
                guess=wrong_guess,
                is_correct=False,
                session=prior_session,
            )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=self.target,
            is_correct=True,
            session=prior_session,
        )

        extra_play = ExtraDailyPlay.objects.create(
            user=self.user,
            game=self.game,
            target=self.target,
            bet_amount=50,
        )
        session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            extra_play=extra_play,
        )
        another_wrong = GameItem.objects.create(game=self.game, name="Another Miss")
        for _ in range(5):
            GameAttempt.objects.create(
                user=self.user,
                game=self.game,
                guess=wrong_guess,
                is_correct=False,
                session=session,
            )

        from apps.games.services.play_session.guess_processor import GuessProcessor
        from django.test import RequestFactory

        factory = RequestFactory()
        request = factory.post("/", {"guess": another_wrong.name})
        request.user = self.user

        is_valid, is_correct, payload = GuessProcessor(self.game, self.user).process(
            request,
            extra_play=extra_play,
        )

        extra_play.refresh_from_db()
        self.assertTrue(is_valid)
        self.assertFalse(is_correct)
        self.assertTrue(extra_play.completed)
        self.assertFalse(payload["bet_won"])

    def test_start_extra_play_deducts_stake(self):
        extra_play = ExtraDailyService(self.user, self.game).start_extra_play(100)

        self.assertEqual(extra_play.bet_amount, 100)
        self.assertEqual(ScoreService(self.user, self.game).score_obj.elo, 0)

    def test_format_extra_bet_goal_uses_integer_threshold(self):
        self.assertEqual(format_extra_bet_goal(4.3), "Menos de 5 intentos")
        self.assertEqual(format_extra_bet_goal(4.0), "Menos de 4 intentos")
        self.assertEqual(format_extra_bet_goal(1.0), "Menos de 1 intento")
        self.assertEqual(format_extra_bet_goal(None), None)

    def test_evaluate_extra_bet_won_when_below_global_average(self):
        for index, username in enumerate(("rival_a", "rival_b"), start=1):
            rival = User.objects.create_user(username=username, password="pass")
            rival_target = GameItem.objects.create(game=self.game, name=f"Rival {index}")
            session = PlaySession.objects.create(
                user=rival,
                game=self.game,
                session_type=PlaySessionType.DAILY,
                reference_id=index,
            )
            for _ in range(4):
                GameAttempt.objects.create(
                    user=rival,
                    game=self.game,
                    guess=rival_target,
                    is_correct=False,
                    session=session,
                )
            GameAttempt.objects.create(
                user=rival,
                game=self.game,
                guess=rival_target,
                is_correct=True,
                session=session,
            )

        score_service = ScoreService(self.user, self.game)
        self.assertTrue(evaluate_extra_bet_won(3, score_service))
        self.assertFalse(evaluate_extra_bet_won(5, score_service))
