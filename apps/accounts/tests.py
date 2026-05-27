from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse

from apps.accounts.models import Challenge, Notification
from apps.accounts.services.notification_service import NotificationService, NotificationType
from apps.games.models import Game, GameItem, PlaySession, PlaySessionType, GameAttempt
from apps.games.services.gameplay.challenge_resolution_service import ChallengeResolutionService


class ChallengeBackendTests(TestCase):

    CHALLENGER_USERNAME = "challenger_user"
    OPPONENT_USERNAME = "opponent_user"
    GAME_NAME = "League of Legends"
    GAME_SLUG = "lol"
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
            accepted=True
        )

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
            },
        )

        self.assertEqual(response.status_code, self.HTTP_OK)
        notification = Notification.objects.filter(
            user=self.opponent,
            type=NotificationType.CHALLENGE_RECEIVED,
        )
        self.assertEqual(notification.count(), 1)

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
        from apps.accounts.services.dashboard_stats import DashboardStats
        from apps.accounts.services.player_stats_service import PlayerStatsService

        dashboard = DashboardStats(self.user)
        user_row = dashboard.calculate_user_statistics()[0]
        ranking_row = dashboard.generate_ranking_per_game()[self.GAME_SLUG][0]

        self.assertEqual(user_row["points"], ranking_row["points"])
        self.assertEqual(user_row["average_attempts"], ranking_row["average_attempts"])
        self.assertEqual(ranking_row["games_finished"], 1)
        self.assertEqual(user_row["average_attempts"], 2.0)

        canonical = PlayerStatsService.get_game_stats(self.user, self.game)
        self.assertEqual(canonical["points"], 120)
        self.assertEqual(canonical["games_finished"], 1)
        self.assertEqual(canonical["average_attempts"], 2.0)

    def test_surrender_attempts_worsen_average_without_adding_finished_game(self):
        from apps.accounts.services.player_stats_service import PlayerStatsService

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
