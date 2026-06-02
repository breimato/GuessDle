from apps.games.services.rosco.answer_normalizer import normalize_answer


def is_answer_correct(answer_text: str, acceptable_answers: list[str]) -> bool:
    normalized = normalize_answer(answer_text)
    if not normalized:
        return False

    normalized_aliases = {normalize_answer(alias) for alias in acceptable_answers if alias}
    return normalized in normalized_aliases
