from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from apps.games.models import (
    Game,
    GameAttempt,
    GameItem,
    GameMode,
    GameModePlayType,
    PlaySession,
    PlaySessionType,
    ProximityAttempt,
    ProximityDailyAssignment,
    SilhouetteDailyAssignment,
)
from apps.games.services.admin.reset_play_service import (
    delete_silhouette_assignments,
    reset_play_session,
    reset_silhouette_assignment,
)


class ResetPlayServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="reset-user", password="pass")
        self.game = Game.objects.create(
            name="Pokemon Reset",
            slug="pokemon-reset",
            data_source_url="https://example.com",
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="silueta",
            play_type=GameModePlayType.SILHOUETTE,
        )
        self.target = GameItem.objects.create(
            game=self.game,
            name="Pikachu",
            data={"id": 25},
        )
        self.guess = GameItem.objects.create(
            game=self.game,
            name="Bulbasaur",
            data={"id": 1},
        )
        self.assignment = SilhouetteDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            target_item=self.target,
            anchor="tl",
        )
        self.session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            session_type=PlaySessionType.SILHOUETTE,
            reference_id=self.assignment.id,
            surrendered=True,
        )
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=self.guess,
            is_correct=False,
            session=self.session,
        )

    def test_reset_play_session_when_surrendered_then_clears_attempts_and_flags(self):
        deleted = reset_play_session(self.session)

        self.session.refresh_from_db()
        self.assertEqual(deleted, 1)
        self.assertFalse(self.session.surrendered)
        self.assertFalse(GameAttempt.objects.filter(session=self.session).exists())

    def test_reset_silhouette_assignment_when_called_then_resets_linked_session(self):
        reset_silhouette_assignment(self.assignment)

        self.session.refresh_from_db()
        self.assertFalse(self.session.surrendered)
        self.assertFalse(GameAttempt.objects.filter(session=self.session).exists())
        self.assertTrue(
            SilhouetteDailyAssignment.objects.filter(pk=self.assignment.pk).exists()
        )

    def test_delete_silhouette_assignments_when_called_then_removes_sessions(self):
        deleted = delete_silhouette_assignments(
            SilhouetteDailyAssignment.objects.filter(pk=self.assignment.pk)
        )

        self.assertEqual(deleted, 1)
        self.assertFalse(
            PlaySession.objects.filter(
                session_type=PlaySessionType.SILHOUETTE,
                reference_id=self.assignment.id,
            ).exists()
        )


class ResetProximitySessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="proximity-reset", password="pass")
        self.game = Game.objects.create(
            name="One Piece Reset",
            slug="one-piece-reset",
            data_source_url="https://example.com",
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="proximidad",
            play_type=GameModePlayType.PROXIMITY,
        )
        self.assignment = ProximityDailyAssignment.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            date=timezone.localdate(),
            answer_value=100,
        )
        self.session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            session_type=PlaySessionType.PROXIMITY,
            reference_id=self.assignment.id,
            proximity_completed=True,
            proximity_score_locked=80,
        )
        ProximityAttempt.objects.create(
            session=self.session,
            guess_value=90,
            distance=10,
        )

    def test_reset_play_session_when_proximity_then_clears_proximity_state(self):
        deleted = reset_play_session(self.session)

        self.session.refresh_from_db()
        self.assertEqual(deleted, 1)
        self.assertFalse(self.session.proximity_completed)
        self.assertIsNone(self.session.proximity_score_locked)
        self.assertFalse(ProximityAttempt.objects.filter(session=self.session).exists())
