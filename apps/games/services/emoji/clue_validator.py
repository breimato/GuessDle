from apps.games.models import MAX_EMOJI_CLUES, MIN_EMOJI_CLUES


class EmojiClueImportError(ValueError):
    pass


def validate_emoji_clues(clues: list, *, source: str = "JSON") -> list[str]:
    if not isinstance(clues, list):
        raise EmojiClueImportError(f"{source}: clues debe ser una lista.")

    if not MIN_EMOJI_CLUES <= len(clues) <= MAX_EMOJI_CLUES:
        raise EmojiClueImportError(
            f"{source}: cada set debe tener entre {MIN_EMOJI_CLUES} y {MAX_EMOJI_CLUES} pistas."
        )

    normalized: list[str] = []
    for index, clue in enumerate(clues, start=1):
        if not isinstance(clue, str) or not clue.strip():
            raise EmojiClueImportError(f"{source}: la pista #{index} no puede estar vacía.")
        normalized.append(clue.strip())
    return normalized


def validate_emoji_clue_payload(payload: list, *, source: str = "JSON") -> None:
    if not isinstance(payload, list):
        raise EmojiClueImportError(f"{source}: debe ser una lista de sets emoji.")

    if not payload:
        raise EmojiClueImportError(f"{source}: la lista está vacía.")

    seen_items: set[str] = set()
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise EmojiClueImportError(f"{source}: entrada #{index} no es un objeto.")

        item_name = str(item.get("item_name", "")).strip()
        if not item_name:
            raise EmojiClueImportError(f"{source}: falta item_name en entrada #{index}.")

        normalized_name = item_name.casefold()
        if normalized_name in seen_items:
            raise EmojiClueImportError(f"{source}: item_name duplicado '{item_name}'.")
        seen_items.add(normalized_name)

        validate_emoji_clues(item.get("clues") or [], source=source)
