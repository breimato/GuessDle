from apps.games.models import Game, GameItem, ProximityDailyAssignment, ProximityPrompt
from apps.games.services.proximity.chapter_episode_lookup import episode_for_chapter
from apps.games.services.proximity.game_config import (
    ONE_PIECE_MEDIA_ANIME,
    ONE_PIECE_MEDIA_MANGA,
    lol_release_year,
    proximity_game_kind,
)


def resolve_assignment_answer(game: Game, assignment: ProximityDailyAssignment) -> int:
    media = (assignment.filter_config or {}).get("media")
    resolver = ProximityAnswerResolver(game, media=media)
    if assignment.target_item_id and assignment.target_item is not None:
        answer = resolver.resolve_item(assignment.target_item)
    elif assignment.proximity_prompt_id and assignment.proximity_prompt is not None:
        answer = resolver.resolve_prompt(assignment.proximity_prompt)
    else:
        answer = None
    if answer is not None:
        return answer
    return int(assignment.answer_value)


class ProximityAnswerResolver:
    def __init__(self, game: Game, media: str | None = None):
        self.game = game
        self.kind = proximity_game_kind(game)
        self.media = media or ONE_PIECE_MEDIA_MANGA

    def resolve_item(self, item: GameItem) -> int | None:
        data = item.data or {}
        if self.kind == "pokemon":
            raw = data.get("id")
        elif self.kind == "lol":
            raw = lol_release_year(data)
        elif self.kind == "one_piece":
            if self.media == ONE_PIECE_MEDIA_ANIME:
                from apps.games.services.catalog.one_piece_episode_utils import (
                    episode_for_character_data,
                )

                return episode_for_character_data(data)
            raw = data.get("capítulo") or data.get("capitulo")
        else:
            return None
        return self._to_int(raw)

    def resolve_prompt(self, prompt: ProximityPrompt) -> int | None:
        if self.kind == "one_piece" and self.media == ONE_PIECE_MEDIA_ANIME:
            if prompt.answer_episode is not None:
                return int(prompt.answer_episode)
            return episode_for_chapter(int(prompt.answer_value))
        return int(prompt.answer_value)

    @staticmethod
    def _to_int(value) -> int | None:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
