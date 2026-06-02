ROSCO_LETTERS: tuple[str, ...] = tuple("ABCDEFGHIJKLMNÑOPQRSTUVWXYZ")


def letter_index(letter: str) -> int:
    normalized = letter.upper()
    try:
        return ROSCO_LETTERS.index(normalized)
    except ValueError as error:
        raise ValueError(f"Letra de rosco no válida: {letter}") from error


def next_letter_in_order(letter: str) -> str | None:
    index = letter_index(letter)
    if index + 1 >= len(ROSCO_LETTERS):
        return None
    return ROSCO_LETTERS[index + 1]


def first_pending_letter(start_after: str | None, letter_states: dict[str, str]) -> str | None:
    if not letter_states:
        return ROSCO_LETTERS[0]

    start_index = 0
    if start_after:
        start_index = letter_index(start_after) + 1

    for offset in range(len(ROSCO_LETTERS)):
        letter = ROSCO_LETTERS[(start_index + offset) % len(ROSCO_LETTERS)]
        if letter_states.get(letter) == "pending":
            return letter
    return None
