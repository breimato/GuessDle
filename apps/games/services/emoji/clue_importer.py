from apps.games.models import EmojiClueSet, Game, GameItem
from apps.games.services.emoji.clue_validator import EmojiClueImportError, validate_emoji_clue_payload


def import_emoji_clues(game: Game, payload: list, *, source: str = "JSON") -> int:
    validate_emoji_clue_payload(payload, source=source)

    upserted = 0
    for item in payload:
        item_name = str(item["item_name"]).strip()
        game_item = GameItem.objects.filter(game=game, name__iexact=item_name, deleted=False).first()
        if not game_item:
            raise EmojiClueImportError(
                f"{source}: no existe el personaje '{item_name}' en {game.slug}."
            )

        clues = [str(clue).strip() for clue in item.get("clues") or [] if str(clue).strip()]
        active = item.get("active", True)

        EmojiClueSet.objects.update_or_create(
            game=game,
            item=game_item,
            defaults={"clues": clues, "active": active},
        )
        upserted += 1
    return upserted
