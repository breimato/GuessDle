import random

from django.contrib.auth.models import User
from django.db import transaction

from apps.games.models import (
    Game,
    GameMode,
    PlaySession,
    PlaySessionType,
    RoscoQuestion,
    RoscoSessionStatus,
    WeeklyRosco,
    WeeklyRoscoEntry,
)
from apps.games.services.rosco.alphabet import ROSCO_LETTERS
from apps.games.services.rosco.week_utils import current_rosco_period_start
from apps.games.services.rosco.weekly_pot_service import WeeklyPotService


class WeeklyRoscoService:
    @staticmethod
    def has_question_bank(game: Game) -> bool:
        letters_with_questions = set(
            RoscoQuestion.objects.filter(game=game, active=True).values_list("letter", flat=True)
        )
        return all(letter in letters_with_questions for letter in ROSCO_LETTERS)

    def __init__(self, game: Game, mode: GameMode, user: User):
        self.game = game
        self.mode = mode
        self.user = user
        self.is_team = bool(getattr(getattr(user, "profile", None), "is_team_account", False))

    def get_current_weekly_rosco(self) -> WeeklyRosco | None:
        week_start = current_rosco_period_start(self.game, self.mode, self.is_team)
        return (
            WeeklyRosco.objects.filter(
                game=self.game,
                mode=self.mode,
                week_start=week_start,
                is_team=self.is_team,
            )
            .select_related("pot")
            .prefetch_related("entries__question")
            .first()
        )

    @transaction.atomic
    def ensure_current_weekly_rosco(self) -> WeeklyRosco:
        existing = self.get_current_weekly_rosco()
        if existing:
            return existing
        return self._create_weekly_rosco(
            current_rosco_period_start(self.game, self.mode, self.is_team)
        )

    def _create_weekly_rosco(self, week_start) -> WeeklyRosco:
        weekly_rosco = WeeklyRosco.objects.create(
            game=self.game,
            mode=self.mode,
            week_start=week_start,
            is_team=self.is_team,
        )
        for index, letter in enumerate(ROSCO_LETTERS):
            question = self._pick_question_for_letter(letter)
            WeeklyRoscoEntry.objects.create(
                weekly_rosco=weekly_rosco,
                letter=letter,
                sort_order=index,
                question=question,
                prompt_snapshot=question.prompt,
            )
        WeeklyPotService(weekly_rosco).initialize_pot()
        return weekly_rosco

    def _pick_question_for_letter(self, letter: str) -> RoscoQuestion:
        queryset = RoscoQuestion.objects.filter(
            game=self.game,
            letter=letter,
            active=True,
        )
        questions = list(queryset)
        if not questions:
            raise ValueError(
                f"No hay preguntas activas para la letra {letter} en {self.game.slug}."
            )
        return random.choice(questions)

    def get_or_create_session(self, weekly_rosco: WeeklyRosco) -> PlaySession:
        session, created = PlaySession.objects.get_or_create(
            user=self.user,
            game=self.game,
            session_type=PlaySessionType.ROSCO,
            reference_id=weekly_rosco.id,
            defaults={
                "mode": self.mode,
                "rosco_current_letter": ROSCO_LETTERS[0],
                "rosco_status": RoscoSessionStatus.IN_PROGRESS,
            },
        )
        if not created and session.mode_id != self.mode.id:
            session.mode = self.mode
            session.save(update_fields=["mode"])
        if created:
            return session

        if not session.rosco_current_letter:
            session.rosco_current_letter = ROSCO_LETTERS[0]
            session.rosco_status = RoscoSessionStatus.IN_PROGRESS
            session.save(update_fields=["rosco_current_letter", "rosco_status"])
        return session

    def get_entry_for_letter(self, weekly_rosco: WeeklyRosco, letter: str) -> WeeklyRoscoEntry | None:
        return weekly_rosco.entries.filter(letter=letter).select_related("question").first()
