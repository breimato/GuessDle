from django.db import transaction

from apps.games.models import RoscoLetterAttempt, RoscoSessionStatus
from apps.games.services.rosco.alphabet import first_pending_letter
from apps.games.services.rosco.answer_validator import is_answer_correct
from apps.games.services.rosco.rosco_session_state import (
    all_letters_correct,
    build_letter_states,
    count_correct_letters,
    no_pending_letters,
    session_is_playable,
)
from apps.games.services.rosco.weekly_pot_service import WeeklyPotService


class RoscoTurnProcessor:
    def __init__(self, session, weekly_rosco, entry):
        self.session = session
        self.weekly_rosco = weekly_rosco
        self.entry = entry

    @staticmethod
    def display_answer(entry) -> str:
        answers = entry.question.acceptable_answers if entry else []
        return answers[0] if answers else ""

    @transaction.atomic
    def process_answer(self, answer_text: str) -> dict:
        if not session_is_playable(self.session):
            return self._build_response(game_over=True)

        letter = self.session.rosco_current_letter
        if RoscoLetterAttempt.objects.filter(session=self.session, letter=letter).exists():
            return self._build_response(error="Esta letra ya fue contestada.")

        correct = is_answer_correct(answer_text, self.entry.question.acceptable_answers)
        RoscoLetterAttempt.objects.create(
            session=self.session,
            letter=letter,
            answer_text=answer_text.strip(),
            is_correct=correct,
        )

        letter_states = build_letter_states(self.session)

        if correct and all_letters_correct(letter_states):
            self.session.rosco_status = RoscoSessionStatus.WON_PERFECT
            self.session.rosco_current_letter = ""
            self.session.save(update_fields=["rosco_status", "rosco_current_letter"])
            WeeklyPotService(self.weekly_rosco).register_perfect_winner(
                self.session.user,
                self.session,
            )
            return self._build_response(
                action="answer",
                is_correct=True,
                game_over=True,
                won_perfect=True,
            )

        if no_pending_letters(letter_states):
            self.session.rosco_status = RoscoSessionStatus.COMPLETED
            self.session.rosco_current_letter = ""
            self.session.save(update_fields=["rosco_status", "rosco_current_letter"])
            return self._build_response(
                action="answer",
                is_correct=correct,
                game_over=True,
                correct_answer=self.display_answer(self.entry) if not correct else None,
            )

        next_letter = first_pending_letter(letter, letter_states)
        self.session.rosco_current_letter = next_letter or ""
        self.session.save(update_fields=["rosco_current_letter"])
        return self._build_response(
            action="answer",
            is_correct=correct,
            game_over=False,
            correct_answer=self.display_answer(self.entry) if not correct else None,
        )

    @transaction.atomic
    def process_pass(self) -> dict:
        if not session_is_playable(self.session):
            return self._build_response(game_over=True)

        letter_states = build_letter_states(self.session)
        current = self.session.rosco_current_letter
        next_letter = first_pending_letter(current, letter_states)
        if not next_letter:
            return self._build_response(error="No quedan letras pendientes.")

        self.session.rosco_current_letter = next_letter
        self.session.save(update_fields=["rosco_current_letter"])
        return self._build_response(action="pass", game_over=False)

    @transaction.atomic
    def process_surrender(self) -> dict:
        if not session_is_playable(self.session):
            return self._build_response(game_over=True)

        self.session.rosco_status = RoscoSessionStatus.SURRENDERED
        self.session.surrendered = True
        self.session.save(update_fields=["rosco_status", "surrendered"])
        return self._build_response(action="surrender", game_over=True)

    def _build_response(
        self,
        *,
        action=None,
        is_correct=None,
        game_over=False,
        won_perfect=False,
        correct_answer=None,
        error=None,
    ) -> dict:
        letter_states = build_letter_states(self.session)
        current_letter = self.session.rosco_current_letter
        if session_is_playable(self.session) and not current_letter:
            current_letter = first_pending_letter(None, letter_states) or ""
            if current_letter:
                self.session.rosco_current_letter = current_letter
                self.session.save(update_fields=["rosco_current_letter"])

        for letter, state in letter_states.items():
            if letter == current_letter and state == "pending" and session_is_playable(self.session):
                letter_states[letter] = "current"

        pot = WeeklyPotService(self.weekly_rosco).get_pot()
        payload = {
            "current_letter": current_letter,
            "letters": letter_states,
            "action": action,
            "is_correct": is_correct,
            "game_over": game_over,
            "won_perfect": won_perfect,
            "pot_amount": pot.pot_amount,
            "correct_count": count_correct_letters(letter_states),
            "session_status": self.session.rosco_status or RoscoSessionStatus.IN_PROGRESS,
            "can_play": session_is_playable(self.session),
            "error": error,
        }
        if correct_answer:
            payload["correct_answer"] = correct_answer
        if current_letter and session_is_playable(self.session):
            entry = self.weekly_rosco.entries.filter(letter=current_letter).first()
            payload["prompt"] = entry.prompt_snapshot if entry else ""
        elif not session_is_playable(self.session):
            payload["prompt"] = ""
        return payload
