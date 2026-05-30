from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import Challenge, GameElo, Notification
from apps.accounts.services.notifications.notification_service import NotificationService
from apps.accounts.services.notifications.notification_types import NotificationType
from apps.games.models import Game, GameItem, PlaySession, PlaySessionType, GameAttempt
from apps.accounts.services.challenges.challenge_resolution_service import ChallengeResolutionService
from apps.accounts.services.challenges.challenger_manager import ChallengeManager
from apps.games.services.play_session.play_session_service import PlaySessionService


class ChallengeBackendTests(TestCase):

    CHALLENGER_USERNAME = "challenger_user"
    OPPONENT_USERNAME = "opponent_user"
    GAME_NAME = "League of Legends"
    GAME_SLUG = "league-of-legends"
    TARGET_NAME = "Ezreal"
    ATTEMPT_COUNT_THREE = 3
    ATTEMPT_COUNT_FIVE = 5
    HTTP_OK = 200
    STATUS_WINNER = "winner"
    STATUS_TIE = "tie"
    STATUS_ALREADY_RESOLVED = "already-resolved"
    POST_ATTEMPTS = "attempts"
    HEADER_X_REQUESTED_WITH = "HTTP_X_REQUESTED_WITH"
    VALUE_XML_HTTP_REQUEST = "XMLHttpRequest"
    USER_PASSWORD = "password123"
    URL_DASHBOARD = "dashboard"
    URL_PLAY_CHALLENGE = "play_challenge"
    URL_NOTIFICATIONS_POLL = "notifications_poll"
    URL_NOTIFICATIONS_ACK = "notifications_ack"
    URL_CREATE_CHALLENGE = "create_challenge"
    URL_ACCEPT_CHALLENGE = "accept_challenge"

    def setUp(self):
        self.challenger = User.objects.create_user(
            username=self.CHALLENGER_USERNAME,
            password=self.USER_PASSWORD
        )
        self.opponent = User.objects.create_user(
            username=self.OPPONENT_USERNAME,
            password=self.USER_PASSWORD
        )
        self.game = Game.objects.create(
            name=self.GAME_NAME,
            slug=self.GAME_SLUG
        )
        self.target = GameItem.objects.create(
            game=self.game,
            name=self.TARGET_NAME
        )
        self.challenge = Challenge.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            game=self.game,
            target=self.target,
            accepted=True,
            stake_points=30,
        )
        GameElo.objects.create(user=self.challenger, game=self.game, elo=100)
        GameElo.objects.create(user=self.opponent, game=self.game, elo=100)

        self.client = Client()

    def test_ajax_post_returns_json_metadata_on_resolution(self):
        self.client.force_login(self.challenger)
        url = reverse(self.URL_PLAY_CHALLENGE, args=[self.challenge.id])

        response = self.client.post(
            url,
            {self.POST_ATTEMPTS: self.ATTEMPT_COUNT_THREE},
            HTTP_X_REQUESTED_WITH=self.VALUE_XML_HTTP_REQUEST
        )

        self.challenge.refresh_from_db()
        self.assertEqual(response.status_code, self.HTTP_OK)
        json_data = response.json()
        self.assertFalse(json_data["completed"])
        self.assertEqual(json_data["result_status"], self.STATUS_ALREADY_RESOLVED)

        self.client.force_login(self.opponent)
        response = self.client.post(
            url,
            {self.POST_ATTEMPTS: self.ATTEMPT_COUNT_FIVE},
            HTTP_X_REQUESTED_WITH=self.VALUE_XML_HTTP_REQUEST
        )

        self.challenge.refresh_from_db()
        self.assertEqual(response.status_code, self.HTTP_OK)
        json_data = response.json()
        self.assertTrue(json_data["completed"])
        self.assertEqual(json_data["winner"], self.CHALLENGER_USERNAME)
        self.assertEqual(json_data["result_status"], self.STATUS_WINNER)

    def test_challenge_resolution_notifies_winner_and_loser(self):
        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_FIVE
        self.challenge.save()

        resolution_service = ChallengeResolutionService(self.challenge, acting_user=self.opponent)
        result = resolution_service.resolve_and_assign_points()

        self.assertEqual(result["status"], self.STATUS_WINNER)
        self.challenge.refresh_from_db()
        self.assertTrue(self.challenge.completed)
        self.assertEqual(self.challenge.winner, self.challenger)

        win_notification = Notification.objects.filter(
            user=self.challenger,
            type=NotificationType.CHALLENGE_WIN,
            challenge=self.challenge,
        )
        self.assertTrue(win_notification.exists())
        self.assertEqual(win_notification.first().payload.get("points_delta"), 30.0)
        self.assertFalse(
            Notification.objects.filter(
                user=self.opponent,
                type=NotificationType.CHALLENGE_WIN,
                challenge=self.challenge,
            ).exists()
        )

    def test_challenge_resolution_notifies_acting_user_on_tie(self):
        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.save()

        resolution_service = ChallengeResolutionService(self.challenge, acting_user=self.challenger)
        result = resolution_service.resolve_and_assign_points()

        self.assertEqual(result["status"], self.STATUS_TIE)
        self.challenge.refresh_from_db()
        self.assertTrue(self.challenge.completed)
        self.assertIsNone(self.challenge.winner)

        tie_notification = Notification.objects.filter(
            user=self.opponent,
            type=NotificationType.CHALLENGE_TIE,
            challenge=self.challenge,
        )
        self.assertTrue(tie_notification.exists())
        self.assertEqual(tie_notification.first().payload.get("points_delta"), -30.0)
        self.assertFalse(
            Notification.objects.filter(
                user=self.challenger,
                type=NotificationType.CHALLENGE_TIE,
                challenge=self.challenge,
            ).exists()
        )

    def test_create_challenge_notifies_opponent(self):
        self.client.force_login(self.challenger)
        response = self.client.post(
            reverse(self.URL_CREATE_CHALLENGE),
            {
                "opponent": self.opponent.id,
                "game": self.game.id,
                "stake_points": 20,
            },
        )

        self.assertEqual(response.status_code, self.HTTP_OK)
        notification = Notification.objects.filter(
            user=self.opponent,
            type=NotificationType.CHALLENGE_RECEIVED,
        )
        self.assertEqual(notification.count(), 1)

    def test_create_challenge_rejects_stake_above_opponent_available_points(self):
        opponent_score = GameElo.objects.get(user=self.opponent, game=self.game, mode__isnull=True)
        opponent_score.elo = 10
        opponent_score.save(update_fields=["elo"])

        self.client.force_login(self.challenger)
        response = self.client.post(
            reverse(self.URL_CREATE_CHALLENGE),
            {
                "opponent": self.opponent.id,
                "game": self.game.id,
                "stake_points": 20,
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")

    def test_accept_challenge_fails_when_opponent_points_are_held(self):
        locked_challenge = Challenge.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            game=self.game,
            target=self.target,
            accepted=True,
            completed=False,
            stake_points=95,
            stake_settled=False,
        )
        self.assertIsNotNone(locked_challenge.pk)

        pending_challenge = Challenge.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            game=self.game,
            target=self.target,
            accepted=False,
            completed=False,
            stake_points=20,
            stake_settled=False,
        )

        self.client.force_login(self.opponent)
        response = self.client.get(reverse(self.URL_PLAY_CHALLENGE, args=[pending_challenge.id]))
        self.assertEqual(response.status_code, 302)

        pending_challenge.refresh_from_db()
        self.assertFalse(pending_challenge.accepted)

    def test_accept_challenge_endpoint_returns_error_when_points_are_held(self):
        Challenge.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            game=self.game,
            target=self.target,
            accepted=True,
            completed=False,
            stake_points=95,
            stake_settled=False,
        )
        pending_challenge = Challenge.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            game=self.game,
            target=self.target,
            accepted=False,
            completed=False,
            stake_points=20,
            stake_settled=False,
        )

        self.client.force_login(self.opponent)
        response = self.client.post(reverse(self.URL_ACCEPT_CHALLENGE, args=[pending_challenge.id]))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["status"], "error")
        pending_challenge.refresh_from_db()
        self.assertFalse(pending_challenge.accepted)

    def test_resolution_transfers_stake_points_to_winner(self):
        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_FIVE
        self.challenge.save(update_fields=["challenger_attempts", "opponent_attempts"])

        resolution_service = ChallengeResolutionService(self.challenge, acting_user=self.challenger)
        result = resolution_service.resolve_and_assign_points()

        self.assertEqual(result["status"], self.STATUS_WINNER)
        self.challenge.refresh_from_db()
        self.assertTrue(self.challenge.stake_settled)
        challenger_score = GameElo.objects.get(user=self.challenger, game=self.game, mode__isnull=True)
        opponent_score = GameElo.objects.get(user=self.opponent, game=self.game, mode__isnull=True)
        self.assertEqual(challenger_score.elo, 130)
        self.assertEqual(opponent_score.elo, 70)

    def test_resolution_tie_deducts_stake_from_both_users(self):
        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.save(update_fields=["challenger_attempts", "opponent_attempts"])

        resolution_service = ChallengeResolutionService(self.challenge, acting_user=self.challenger)
        result = resolution_service.resolve_and_assign_points()

        self.assertEqual(result["status"], self.STATUS_TIE)
        challenger_score = GameElo.objects.get(user=self.challenger, game=self.game, mode__isnull=True)
        opponent_score = GameElo.objects.get(user=self.opponent, game=self.game, mode__isnull=True)
        self.assertEqual(challenger_score.elo, 70)
        self.assertEqual(opponent_score.elo, 70)

    def test_winner_when_one_solves_and_other_surrenders_with_same_attempt_count(self):
        wrong_guess = GameItem.objects.create(game=self.game, name="Wrong Guess")
        self.challenge.stake_points = 100
        self.challenge.save(update_fields=["stake_points"])

        challenger_session = PlaySessionService.get_or_create(
            self.challenger,
            self.game,
            challenge=self.challenge,
        )
        opponent_session = PlaySessionService.get_or_create(
            self.opponent,
            self.game,
            challenge=self.challenge,
        )
        GameAttempt.objects.create(
            user=self.challenger,
            game=self.game,
            session=challenger_session,
            guess=self.target,
            is_correct=True,
        )
        GameAttempt.objects.create(
            user=self.opponent,
            game=self.game,
            session=opponent_session,
            guess=wrong_guess,
            is_correct=False,
        )
        opponent_session.surrendered = True
        opponent_session.save(update_fields=["surrendered"])

        self.challenge.challenger_attempts = 1
        self.challenge.opponent_attempts = 1
        self.challenge.save(update_fields=["challenger_attempts", "opponent_attempts"])

        ChallengeManager(user=self.opponent, challenge=self.challenge).calculate_winner()
        self.challenge.refresh_from_db()

        self.assertTrue(self.challenge.completed)
        self.assertEqual(self.challenge.winner, self.challenger)

        resolution_result = ChallengeResolutionService(
            self.challenge, acting_user=self.opponent
        ).resolve_and_assign_points()
        self.assertEqual(resolution_result["status"], self.STATUS_WINNER)
        self.assertEqual(
            resolution_result["point_deltas"][self.OPPONENT_USERNAME],
            -100.0,
        )

    def test_resolution_is_idempotent_after_stake_settlement(self):
        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_FIVE
        self.challenge.save(update_fields=["challenger_attempts", "opponent_attempts"])

        resolution_service = ChallengeResolutionService(self.challenge, acting_user=self.challenger)
        first_result = resolution_service.resolve_and_assign_points()
        second_result = resolution_service.resolve_and_assign_points()

        self.assertEqual(first_result["status"], self.STATUS_WINNER)
        self.assertEqual(second_result["status"], self.STATUS_WINNER)
        challenger_score = GameElo.objects.get(user=self.challenger, game=self.game, mode__isnull=True)
        opponent_score = GameElo.objects.get(user=self.opponent, game=self.game, mode__isnull=True)
        self.assertEqual(challenger_score.elo, 130)
        self.assertEqual(opponent_score.elo, 70)

    def test_notification_create_deduplicates_unread_challenge_notifications(self):
        NotificationService.create(
            self.opponent,
            NotificationType.CHALLENGE_RECEIVED,
            NotificationService.challenge_payload(self.challenge, self.challenger.username),
            self.challenge,
        )
        duplicate = NotificationService.create(
            self.opponent,
            NotificationType.CHALLENGE_RECEIVED,
            NotificationService.challenge_payload(self.challenge, self.challenger.username),
            self.challenge,
        )

        self.assertIsNone(duplicate)
        self.assertEqual(
            Notification.objects.filter(
                user=self.opponent,
                type=NotificationType.CHALLENGE_RECEIVED,
                challenge=self.challenge,
                read_at__isnull=True,
            ).count(),
            1,
        )

    def test_notifications_poll_and_ack(self):
        NotificationService.create(
            self.challenger,
            NotificationType.CHALLENGE_WIN,
            {
                "challenge_id": self.challenge.id,
                "game_name": self.game.name,
                "opponent_username": self.opponent.username,
            },
            self.challenge,
        )

        self.client.force_login(self.challenger)
        poll_response = self.client.get(reverse(self.URL_NOTIFICATIONS_POLL))
        self.assertEqual(poll_response.status_code, self.HTTP_OK)
        poll_data = poll_response.json()
        self.assertEqual(len(poll_data["notifications"]), 1)
        notification_id = poll_data["notifications"][0]["id"]

        ack_response = self.client.post(
            reverse(self.URL_NOTIFICATIONS_ACK),
            {"ids": str(notification_id)},
        )
        self.assertEqual(ack_response.status_code, self.HTTP_OK)

        poll_response = self.client.get(reverse(self.URL_NOTIFICATIONS_POLL))
        poll_data = poll_response.json()
        self.assertEqual(len(poll_data["notifications"]), 0)

    def test_notifications_poll_includes_stats_and_rankings_when_requested(self):
        self.client.force_login(self.challenger)
        poll_response = self.client.get(
            reverse(self.URL_NOTIFICATIONS_POLL),
            {
                "include_stats": "1",
                "include_rankings": "1",
            },
        )
        self.assertEqual(poll_response.status_code, self.HTTP_OK)
        payload = poll_response.json()
        self.assertEqual(payload["status"], "ok")
        self.assertIn("stats_sync", payload)
        self.assertIn("ranking_sync", payload)
        self.assertIn("games", payload["stats_sync"])
        self.assertIn("global_elo", payload["stats_sync"])
        self.assertIn("global_ranking", payload["ranking_sync"])
        self.assertIn("ranking_by_game", payload["ranking_sync"])

    def test_reject_challenge_notifies_challenger(self):
        pending = Challenge.objects.create(
            challenger=self.challenger,
            opponent=self.opponent,
            game=self.game,
            target=self.target,
        )

        self.client.force_login(self.opponent)
        response = self.client.post(reverse("reject_challenge", args=[pending.id]))
        self.assertEqual(response.status_code, self.HTTP_OK)

        notification = Notification.objects.filter(
            user=self.challenger,
            type=NotificationType.CHALLENGE_REJECTED,
        )
        self.assertEqual(notification.count(), 1)
        self.assertEqual(notification.first().payload["challenge_id"], pending.id)

    def test_notify_rival_finished_skips_when_recipient_already_finished(self):
        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_FIVE
        self.challenge.save(update_fields=["challenger_attempts", "opponent_attempts"])

        NotificationService.notify_rival_finished(self.challenge, self.challenger)

        notification = Notification.objects.filter(
            user=self.opponent,
            type=NotificationType.RIVAL_FINISHED,
            challenge=self.challenge,
        )
        self.assertFalse(notification.exists())


class PlayerStatsServiceTests(TestCase):

    USERNAME = "stats_user"
    GAME_NAME = "Test Game"
    GAME_SLUG = "test-game"
    TARGET_NAME = "Hero"

    def setUp(self):
        self.user = User.objects.create_user(username=self.USERNAME, password="pass")
        self.game = Game.objects.create(name=self.GAME_NAME, slug=self.GAME_SLUG, active=True)
        self.target = GameItem.objects.create(game=self.game, name=self.TARGET_NAME)
        from apps.accounts.models import GameElo

        GameElo.objects.create(user=self.user, game=self.game, elo=120)

        won_session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=1,
        )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=self.target,
            is_correct=False,
            session=won_session,
        )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=self.target,
            is_correct=True,
            session=won_session,
        )

        lost_session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=2,
        )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=self.target,
            is_correct=False,
            session=lost_session,
        )

    def test_dashboard_and_ranking_stats_match(self):
        from apps.accounts.services.dashboard.player_stats_service import PlayerStatsService

        user_row = PlayerStatsService.get_user_games_stats(self.user)[0]
        ranking_row = PlayerStatsService.build_ranking_per_game()[self.GAME_SLUG][0]

        self.assertEqual(user_row["points"], ranking_row["points"])
        self.assertEqual(user_row["average_attempts"], ranking_row["average_attempts"])
        self.assertEqual(ranking_row["games_finished"], 1)
        self.assertEqual(user_row["average_attempts"], 2.0)

        canonical = PlayerStatsService.get_game_stats(self.user, self.game)
        self.assertEqual(canonical["points"], 120)
        self.assertEqual(canonical["games_finished"], 1)
        self.assertEqual(canonical["average_attempts"], 2.0)

    def test_surrender_attempts_worsen_average_without_adding_finished_game(self):
        from apps.accounts.services.dashboard.player_stats_service import PlayerStatsService

        surrendered_session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.DAILY,
            reference_id=3,
            surrendered=True,
        )
        wrong_guess = GameItem.objects.create(game=self.game, name="Wrong Hero")
        for _ in range(4):
            GameAttempt.objects.create(
                user=self.user,
                game=self.game,
                guess=wrong_guess,
                is_correct=False,
                session=surrendered_session,
            )

        stats = PlayerStatsService.get_game_stats(self.user, self.game)

        self.assertEqual(stats["games_finished"], 1)
        self.assertEqual(stats["average_attempts"], 6.0)


class RegistrationTests(TestCase):
    URL_REGISTER = "register"
    URL_LOGIN = "login"
    USER_PASSWORD = "password123"

    def test_register_when_valid_payload_then_creates_user_without_email(self):
        response = self.client.post(
            reverse(self.URL_REGISTER),
            {
                "username": "new_player",
                "first_name": "Breixo",
                "password1": self.USER_PASSWORD,
                "password2": self.USER_PASSWORD,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse(self.URL_LOGIN))
        user = User.objects.get(username="new_player")
        self.assertEqual(user.email, "")
        self.assertEqual(user.first_name, "Breixo")
