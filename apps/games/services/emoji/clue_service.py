from apps.games.models import EmojiClueSet, Game, GameItem


class EmojiClueService:
    @staticmethod
    def get_active_clue_set(game: Game, item: GameItem) -> EmojiClueSet | None:
        return (
            EmojiClueSet.objects.filter(game=game, item=item, active=True)
            .select_related("item")
            .first()
        )

    @staticmethod
    def get_clues(game: Game, item: GameItem) -> list[str]:
        clue_set = EmojiClueService.get_active_clue_set(game, item)
        if not clue_set:
            return []
        return list(clue_set.clues or [])

    @staticmethod
    def visible_clues(clues: list[str], revealed_count: int) -> list[str]:
        if not clues:
            return []
        return clues[: max(1, min(revealed_count, len(clues)))]

    @staticmethod
    def next_revealed_count(current_count: int, max_clues: int) -> int:
        return min(current_count + 1, max_clues)
