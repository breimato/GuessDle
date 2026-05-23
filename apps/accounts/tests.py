from django.contrib.auth.models import User
from django.test import TestCase, Client
from django.urls import reverse
from apps.accounts.models import Challenge
from apps.games.models import Game, GameItem
from apps.games.services.gameplay.challenge_resolution_service import ChallengeResolutionService


class ChallengeBackendTests(TestCase):
    """Test suite for the challenge modal backend features."""

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

    def setUp(self):
        """Set up test data before each test case."""

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
        """Verify that an AJAX POST request to play_challenge_game view returns challenge completion metadata."""

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
        self.assertEqual(json_data["challenger"], self.CHALLENGER_USERNAME)
        self.assertEqual(json_data["opponent"], self.OPPONENT_USERNAME)
        self.assertEqual(json_data["current_user"], self.OPPONENT_USERNAME)
        self.assertEqual(json_data["result_status"], self.STATUS_WINNER)

    def test_challenge_resolution_notifies_winner_and_loser(self):
        """Verify that resolving a challenge immediately notifies the active player."""

        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_FIVE
        self.challenge.save()

        resolution_service = ChallengeResolutionService(self.challenge, acting_user=self.opponent)
        result = resolution_service.resolve_and_assign_points()

        self.assertEqual(result["status"], self.STATUS_WINNER)
        self.challenge.refresh_from_db()
        self.assertTrue(self.challenge.completed)
        self.assertEqual(self.challenge.winner, self.challenger)
        self.assertTrue(self.challenge.loser_notified)
        self.assertFalse(self.challenge.winner_notified)

    def test_challenge_resolution_notifies_acting_user_on_tie(self):
        """Verify that resolving a tie immediately notifies the acting player."""

        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.save()

        resolution_service = ChallengeResolutionService(self.challenge, acting_user=self.challenger)
        result = resolution_service.resolve_and_assign_points()

        self.assertEqual(result["status"], self.STATUS_TIE)
        self.challenge.refresh_from_db()
        self.assertTrue(self.challenge.completed)
        self.assertIsNone(self.challenge.winner)
        self.assertTrue(self.challenge.winner_notified)
        self.assertFalse(self.challenge.loser_notified)

    def test_dashboard_view_queries_and_tracks_ties(self):
        """Verify dashboard_view fetches, marks, and appends tie notifications."""

        self.challenge.completed = True
        self.challenge.challenger_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.opponent_attempts = self.ATTEMPT_COUNT_THREE
        self.challenge.winner = None
        self.challenge.winner_notified = False
        self.challenge.loser_notified = True
        self.challenge.save()

        self.client.force_login(self.challenger)
        url = reverse(self.URL_DASHBOARD)
        response = self.client.get(url)

        self.assertEqual(response.status_code, self.HTTP_OK)
        notifications = response.context["challenge_notifications"]
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]["type"], self.STATUS_TIE)
        self.assertEqual(notifications[0]["opponent_username"], self.OPPONENT_USERNAME)

        self.challenge.refresh_from_db()
        self.assertTrue(self.challenge.winner_notified)
