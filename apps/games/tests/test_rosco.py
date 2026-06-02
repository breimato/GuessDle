from datetime import date
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import Client, TestCase
from django.urls import reverse

from apps.games.models import (
    Game,
    GameMode,
    GameModePlayType,
    PlaySession,
    PlaySessionType,
    RoscoLetterAttempt,
    RoscoQuestion,
    RoscoSessionStatus,
    WeeklyRosco,
    WeeklyRoscoEntry,
)
from apps.games.services.rosco.alphabet import ROSCO_LETTERS, first_pending_letter
from apps.games.services.rosco.answer_normalizer import normalize_answer
from apps.games.services.rosco.answer_validator import is_answer_correct
from apps.games.services.rosco.rosco_turn_processor import RoscoTurnProcessor
from apps.games.services.rosco.weekly_pot_service import WeeklyPotService
from apps.games.services.rosco.week_utils import (
    current_rosco_saturday,
    is_rosco_play_day,
    rosco_week_number,
    week_label,
)
from apps.games.services.rosco.weekly_rosco_service import WeeklyRoscoService


class RoscoWeekUtilsTests(TestCase):
    SATURDAY = date(2025, 6, 7)

    def setUp(self):
        self.user = User.objects.create_user(username="week_user", password="pass")
        self.game = Game.objects.create(
            name="LoL Week",
            slug="lol-week",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="pasapalabra",
            label="Pasapalabra",
            play_type=GameModePlayType.ROSCO,
        )
        for letter in ROSCO_LETTERS:
            RoscoQuestion.objects.create(
                game=self.game,
                letter=letter,
                question_type="starts_with",
                prompt=f"Pregunta {letter}",
                acceptable_answers=[f"ok {letter.lower()}"],
            )

    @patch("apps.games.services.rosco.week_utils.timezone.localdate", return_value=SATURDAY)
    def test_first_rosco_period_is_week_one(self, _mock_date):
        service = WeeklyRoscoService(self.game, self.mode, self.user)
        weekly = service.ensure_current_weekly_rosco()
        self.assertEqual(weekly.week_start, self.SATURDAY)
        self.assertEqual(rosco_week_number(weekly), 1)
        self.assertEqual(week_label(weekly), "Semana 1")

    def test_current_rosco_saturday_snaps_to_previous_saturday(self):
        monday = date(2025, 6, 9)
        self.assertEqual(current_rosco_saturday(monday), self.SATURDAY)

    def test_is_rosco_play_day_only_on_saturday(self):
        with self.settings(ROSCO_PLAY_WEEKDAYS=[5]):
            self.assertTrue(is_rosco_play_day(self.SATURDAY))
            self.assertFalse(is_rosco_play_day(date(2025, 6, 3)))


class RoscoQuestionBankTests(TestCase):
    def setUp(self):
        self.game = Game.objects.create(
            name="LoL Bank",
            slug="lol-bank",
            data_source_url="https://example.com",
            attributes=["role"],
        )

    def test_has_question_bank_requires_all_letters(self):
        RoscoQuestion.objects.create(
            game=self.game,
            letter="A",
            question_type="starts_with",
            prompt="Pregunta A",
            acceptable_answers=["a"],
        )
        self.assertFalse(WeeklyRoscoService.has_question_bank(self.game))

    def test_has_question_bank_true_when_complete(self):
        for letter in ROSCO_LETTERS:
            RoscoQuestion.objects.create(
                game=self.game,
                letter=letter,
                question_type="starts_with",
                prompt=f"Pregunta {letter}",
                acceptable_answers=[f"ok {letter.lower()}"],
            )
        self.assertTrue(WeeklyRoscoService.has_question_bank(self.game))


class RoscoAnswerNormalizerTests(TestCase):
    def test_normalize_answer_strips_accents_and_case(self):
        self.assertEqual(normalize_answer("  Áurelión Sól  "), "aurelion sol")

    def test_is_answer_correct_accepts_alias(self):
        self.assertTrue(
            is_answer_correct("AURELION", ["aurelion sol", "aurelion"])
        )


class RoscoTurnProcessorTests(TestCase):
    SATURDAY = date(2025, 6, 7)

    def setUp(self):
        self.user = User.objects.create_user(username="rosco_player", password="pass")
        self.game = Game.objects.create(
            name="LoL Test",
            slug="lol-test",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="pasapalabra",
            label="Pasapalabra",
            play_type=GameModePlayType.ROSCO,
            sort_order=5,
        )
        for letter in ROSCO_LETTERS:
            RoscoQuestion.objects.create(
                game=self.game,
                letter=letter,
                question_type="starts_with",
                prompt=f"Pregunta {letter}",
                acceptable_answers=[f"respuesta {letter.lower()}"],
            )

        service = WeeklyRoscoService(self.game, self.mode, self.user)
        with patch(
            "apps.games.services.rosco.week_utils.timezone.localdate",
            return_value=self.SATURDAY,
        ):
            self.weekly_rosco = service.ensure_current_weekly_rosco()
        self.session = service.get_or_create_session(self.weekly_rosco)

    def _entry(self, letter: str) -> WeeklyRoscoEntry:
        return self.weekly_rosco.entries.get(letter=letter)

    def test_pass_advances_without_marking_failure(self):
        processor = RoscoTurnProcessor(self.session, self.weekly_rosco, self._entry("A"))
        result = processor.process_pass()

        self.assertFalse(result["game_over"])
        self.assertEqual(result["current_letter"], "B")
        self.assertEqual(result["letters"]["A"], "pending")

    def test_wrong_answer_advances_without_ending_session(self):
        processor = RoscoTurnProcessor(self.session, self.weekly_rosco, self._entry("A"))
        result = processor.process_answer("mal")

        self.session.refresh_from_db()
        self.assertFalse(result["game_over"])
        self.assertEqual(self.session.rosco_status, RoscoSessionStatus.IN_PROGRESS)
        self.assertEqual(result["letters"]["A"], "wrong")
        self.assertEqual(result["current_letter"], "B")
        self.assertEqual(result["correct_answer"], "respuesta a")

    def test_completed_when_all_letters_attempted_with_a_wrong(self):
        letter_states = {letter: "correct" for letter in ROSCO_LETTERS}
        letter_states[ROSCO_LETTERS[-1]] = "pending"
        letter_states["A"] = "wrong"

        for letter in ROSCO_LETTERS[:-1]:
            if letter == "A":
                continue
            RoscoLetterAttempt.objects.create(
                session=self.session,
                letter=letter,
                answer_text="ok",
                is_correct=True,
            )
        RoscoLetterAttempt.objects.create(
            session=self.session,
            letter="A",
            answer_text="mal",
            is_correct=False,
        )

        self.session.rosco_current_letter = ROSCO_LETTERS[-1]
        self.session.save(update_fields=["rosco_current_letter"])

        processor = RoscoTurnProcessor(
            self.session,
            self.weekly_rosco,
            self._entry(ROSCO_LETTERS[-1]),
        )
        result = processor.process_answer(f"respuesta {ROSCO_LETTERS[-1].lower()}")

        self.session.refresh_from_db()
        self.assertTrue(result["game_over"])
        self.assertEqual(self.session.rosco_status, RoscoSessionStatus.COMPLETED)
        self.assertFalse(result.get("won_perfect"))

    def test_correct_answer_marks_green_and_advances(self):
        processor = RoscoTurnProcessor(self.session, self.weekly_rosco, self._entry("A"))
        result = processor.process_answer("respuesta a")

        self.assertFalse(result["game_over"])
        self.assertEqual(result["letters"]["A"], "correct")
        self.assertEqual(result["current_letter"], "B")

    def test_first_pending_wraps_after_last_letter(self):
        letter_states = {letter: "pending" for letter in ROSCO_LETTERS}
        letter_states["A"] = "correct"
        for letter in ROSCO_LETTERS[1:-1]:
            letter_states[letter] = "correct"
        letter_states[ROSCO_LETTERS[-1]] = "pending"

        self.assertEqual(
            first_pending_letter(ROSCO_LETTERS[-2], letter_states),
            ROSCO_LETTERS[-1],
        )


class RoscoWeeklyPotTests(TestCase):
    SATURDAY = date(2025, 6, 7)

    def setUp(self):
        self.user = User.objects.create_user(username="pot_player", password="pass")
        self.game = Game.objects.create(
            name="LoL Pot",
            slug="lol-pot",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="pasapalabra",
            label="Pasapalabra",
            play_type=GameModePlayType.ROSCO,
        )
        for letter in ROSCO_LETTERS:
            RoscoQuestion.objects.create(
                game=self.game,
                letter=letter,
                question_type="starts_with",
                prompt=f"Pregunta {letter}",
                acceptable_answers=[f"ok {letter.lower()}"],
            )

    @patch("apps.games.services.rosco.week_utils.timezone.localdate", return_value=SATURDAY)
    def test_pot_initializes_with_weekly_contribution(self, _mock_date):
        service = WeeklyRoscoService(self.game, self.mode, self.user)
        weekly = service.ensure_current_weekly_rosco()
        pot = WeeklyPotService(weekly).get_pot()
        self.assertGreaterEqual(pot.pot_amount, WeeklyPotService.weekly_contribution_amount())

    @patch("apps.games.services.rosco.week_utils.timezone.localdate", return_value=SATURDAY)
    def test_perfect_winner_is_registered(self, _mock_date):
        service = WeeklyRoscoService(self.game, self.mode, self.user)
        weekly = service.ensure_current_weekly_rosco()
        session = PlaySession.objects.create(
            user=self.user,
            game=self.game,
            mode=self.mode,
            session_type=PlaySessionType.ROSCO,
            reference_id=weekly.id,
            rosco_status=RoscoSessionStatus.WON_PERFECT,
        )
        winner = WeeklyPotService(weekly).register_perfect_winner(self.user, session)
        self.assertEqual(winner.user, self.user)


class LolModeSelectTests(TestCase):
    SATURDAY = date(2025, 6, 7)

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="lol_selector", password="pass")
        self.client.login(username="lol_selector", password="pass")
        self.game = Game.objects.create(
            name="LoL Select",
            slug="lol-select",
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
        GameMode.objects.create(
            game=self.game,
            slug="pasapalabra",
            label="Pasapalabra",
            play_type=GameModePlayType.ROSCO,
            sort_order=1,
        )
        for letter in ROSCO_LETTERS:
            RoscoQuestion.objects.create(
                game=self.game,
                letter=letter,
                question_type="starts_with",
                prompt=f"Pregunta {letter}",
                acceptable_answers=[f"ok {letter.lower()}"],
            )

    def test_play_without_mode_shows_mode_select_without_pasapalabra_for_normal_user(self):
        response = self.client.get(reverse("play", args=[self.game.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Diario")
        self.assertNotContains(response, "Pasapalabra")
        self.assertContains(response, "mode-select-modes")

    @patch("apps.games.services.rosco.rosco_access.timezone.localdate", return_value=SATURDAY)
    def test_team_user_sees_pasapalabra_on_saturday(self, _mock_date):
        self.user.profile.is_team_account = True
        self.user.profile.save(update_fields=["is_team_account"])

        response = self.client.get(reverse("play", args=[self.game.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pasapalabra")

    @patch("apps.games.services.rosco.rosco_access.timezone.localdate")
    def test_team_user_does_not_see_pasapalabra_on_weekday(self, mock_date):
        mock_date.return_value = date(2025, 6, 2)
        self.user.profile.is_team_account = True
        self.user.profile.save(update_fields=["is_team_account"])

        response = self.client.get(reverse("play", args=[self.game.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Pasapalabra")

    @patch("apps.games.services.rosco.rosco_access.timezone.localdate", return_value=SATURDAY)
    def test_league_mode_select_includes_ahri_media(self, _mock_date):
        self.user.profile.is_team_account = True
        self.user.profile.save(update_fields=["is_team_account"])
        self.game.slug = "league-of-legends"
        self.game.save(update_fields=["slug"])

        response = self.client.get(reverse("play", args=[self.game.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "lol-launcher")
        self.assertContains(response, "lol-launcher__panel")
        self.assertContains(response, "lol-logo.png")
        self.assertContains(response, "audio/ahri_song.mp3")
        self.assertContains(response, "GuessDleBgmPage")
        self.assertContains(response, "Volver al panel")
        self.assertNotContains(response, "trainer-red.png")


class RoscoViewTests(TestCase):
    SATURDAY = date(2025, 6, 7)

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="rosco_viewer", password="pass")
        self.client.login(username="rosco_viewer", password="pass")
        self.game = Game.objects.create(
            name="LoL Views",
            slug="lol-views",
            data_source_url="https://example.com",
            attributes=["role"],
        )
        self.mode = GameMode.objects.create(
            game=self.game,
            slug="pasapalabra",
            label="Pasapalabra",
            play_type=GameModePlayType.ROSCO,
        )
        self.user.profile.is_team_account = True
        self.user.profile.save(update_fields=["is_team_account"])
        for letter in ROSCO_LETTERS:
            RoscoQuestion.objects.create(
                game=self.game,
                letter=letter,
                question_type="starts_with",
                prompt=f"Pregunta {letter}",
                acceptable_answers=[f"respuesta {letter.lower()}"],
            )

    @patch("apps.games.services.rosco.rosco_access.timezone.localdate", return_value=SATURDAY)
    def test_play_page_highlights_current_letter(self, _mock_date):
        response = self.client.get(reverse("play_mode", args=[self.game.slug, self.mode.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'rosco-letter--current')
        self.assertContains(response, "rosco-spoke")
        self.assertContains(response, "rosco-header")
        self.assertContains(response, "rosco-pot-amount")
        self.assertContains(response, "rosco-wheel__center")
        self.assertContains(response, "Letra actual")
        self.assertNotContains(response, "Semana")
        self.assertNotContains(response, "rosco-bokeh")
        self.assertNotContains(response, "rosco-stats")

    @patch("apps.games.services.rosco.rosco_access.timezone.localdate", return_value=SATURDAY)
    def test_answer_endpoint_advances_letter(self, _mock_date):
        url = reverse("rosco_answer", args=[self.game.slug, self.mode.slug])
        response = self.client.post(url, {"answer": "respuesta a"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["letters"]["A"], "correct")
        self.assertEqual(payload["current_letter"], "B")

    @patch("apps.games.services.rosco.rosco_access.timezone.localdate", return_value=SATURDAY)
    def test_play_redirects_when_question_bank_missing(self, _mock_date):
        RoscoQuestion.objects.filter(game=self.game).delete()
        response = self.client.get(reverse("play_mode", args=[self.game.slug, self.mode.slug]))
        self.assertEqual(response.status_code, 302)

    @patch("apps.games.services.rosco.rosco_access.timezone.localdate", return_value=SATURDAY)
    def test_non_team_user_is_redirected(self, _mock_date):
        self.user.profile.is_team_account = False
        self.user.profile.save(update_fields=["is_team_account"])

        response = self.client.get(reverse("play_mode", args=[self.game.slug, self.mode.slug]))

        self.assertEqual(response.status_code, 302)

    @patch("apps.games.services.rosco.rosco_access.timezone.localdate")
    def test_team_user_is_redirected_on_weekday(self, mock_date):
        mock_date.return_value = date(2025, 6, 2)

        response = self.client.get(reverse("play_mode", args=[self.game.slug, self.mode.slug]))

        self.assertEqual(response.status_code, 302)
