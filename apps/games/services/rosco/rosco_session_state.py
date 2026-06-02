from apps.games.models import PlaySession, RoscoLetterAttempt, RoscoSessionStatus
from apps.games.services.rosco.alphabet import ROSCO_LETTERS, first_pending_letter


def build_letter_states(session: PlaySession) -> dict[str, str]:
    attempts = {
        attempt.letter: attempt
        for attempt in RoscoLetterAttempt.objects.filter(session=session)
    }
    states: dict[str, str] = {}
    for letter in ROSCO_LETTERS:
        attempt = attempts.get(letter)
        if attempt is None:
            states[letter] = "pending"
        elif attempt.is_correct:
            states[letter] = "correct"
        else:
            states[letter] = "wrong"
    return states


def count_correct_letters(letter_states: dict[str, str]) -> int:
    return sum(1 for state in letter_states.values() if state == "correct")


def all_letters_correct(letter_states: dict[str, str]) -> bool:
    return all(state == "correct" for state in letter_states.values())


def session_is_playable(session: PlaySession) -> bool:
    return session.rosco_status in ("", RoscoSessionStatus.IN_PROGRESS)


def no_pending_letters(letter_states: dict[str, str]) -> bool:
    return first_pending_letter(None, letter_states) is None


def resolve_current_letter(session: PlaySession, letter_states: dict[str, str]) -> str | None:
    if session.rosco_current_letter and letter_states.get(session.rosco_current_letter) == "pending":
        return session.rosco_current_letter
    return first_pending_letter(None, letter_states)
