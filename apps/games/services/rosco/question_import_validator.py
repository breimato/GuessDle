from apps.games.models import RoscoQuestionType
from apps.games.services.rosco.alphabet import ROSCO_LETTERS
from apps.games.services.rosco.answer_normalizer import normalize_answer


class RoscoQuestionImportError(ValueError):
    pass


def validate_rosco_question_payload(payload: list, *, source: str = "JSON") -> None:
    if not isinstance(payload, list):
        raise RoscoQuestionImportError(f"{source}: debe ser una lista de preguntas.")

    if not payload:
        raise RoscoQuestionImportError(f"{source}: la lista está vacía.")

    seen_letters: set[str] = set()
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise RoscoQuestionImportError(f"{source}: entrada #{index} no es un objeto.")

        letter = str(item.get("letter", "")).upper()
        if letter not in ROSCO_LETTERS:
            raise RoscoQuestionImportError(
                f"{source}: letra inválida '{item.get('letter')}' en entrada #{index}."
            )
        if letter in seen_letters:
            raise RoscoQuestionImportError(
                f"{source}: letra duplicada '{letter}' en entrada #{index}."
            )
        seen_letters.add(letter)

        prompt = item.get("prompt")
        if not prompt or not str(prompt).strip():
            raise RoscoQuestionImportError(f"{source}: falta prompt en letra {letter}.")

        question_type = item.get("question_type", RoscoQuestionType.STARTS_WITH)
        valid_types = {choice.value for choice in RoscoQuestionType}
        if question_type not in valid_types:
            raise RoscoQuestionImportError(
                f"{source}: question_type inválido '{question_type}' en letra {letter}."
            )
        if letter == "Ñ" and question_type != RoscoQuestionType.CONTAINS:
            raise RoscoQuestionImportError(
                f"{source}: la letra Ñ debe usar question_type 'contains'."
            )
        if letter != "Ñ" and question_type != RoscoQuestionType.STARTS_WITH:
            raise RoscoQuestionImportError(
                f"{source}: la letra {letter} debe usar question_type 'starts_with'."
            )

        answers = item.get("acceptable_answers") or []
        normalized = {normalize_answer(answer) for answer in answers if answer}
        if not normalized:
            raise RoscoQuestionImportError(
                f"{source}: letra {letter} sin acceptable_answers válidas."
            )

    missing = [letter for letter in ROSCO_LETTERS if letter not in seen_letters]
    if missing:
        raise RoscoQuestionImportError(
            f"{source}: faltan letras obligatorias: {', '.join(missing)}."
        )
