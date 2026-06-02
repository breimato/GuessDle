from apps.games.models import Game, RoscoQuestion
from apps.games.services.rosco.answer_normalizer import normalize_answer
from apps.games.services.rosco.question_import_validator import (
    RoscoQuestionImportError,
    validate_rosco_question_payload,
)


def import_rosco_questions(game: Game, payload: list, *, source: str = "JSON") -> int:
    validate_rosco_question_payload(payload, source=source)

    created = 0
    for item in payload:
        answers = item.get("acceptable_answers") or []
        normalized = sorted({normalize_answer(answer) for answer in answers if answer})
        if not normalized:
            raise RoscoQuestionImportError(
                f"{source}: letra {item.get('letter')} sin respuestas válidas."
            )

        RoscoQuestion.objects.create(
            game=game,
            letter=str(item["letter"]).upper(),
            question_type=item.get("question_type", "starts_with"),
            prompt=item["prompt"],
            acceptable_answers=list(answers),
            category=item.get("category", ""),
            active=item.get("active", True),
        )
        created += 1
    return created
