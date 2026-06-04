from django.urls import reverse

from apps.games.models import Game, GameAttempt, GameMode
from apps.games.services.catalog.item_pool_service import ItemPoolService
from apps.games.services.catalog.play_mode_navigation import next_mode_navigation
from apps.games.services.catalog.play_background import resolve_background_url
from apps.games.services.daily.target_service import TargetService
from apps.games.services.emoji.clue_service import EmojiClueService
from apps.games.services.emoji.guess_processor import EmojiGuessProcessor
from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.play_session_service import PlaySessionService
from apps.games.services.play_session.play_url_registry import PlayUrlRegistry


class EmojiContextBuilder:
    def __init__(self, request, game: Game, mode: GameMode, daily_target):
        self.request = request
        self.game = game
        self.mode = mode
        self.daily_target = daily_target
        self.user = request.user

    def build(self) -> dict:
        play_context = PlayContext.exactly_one(daily_target=self.daily_target)
        target_item = play_context.target
        clues = EmojiClueService.get_clues(self.game, target_item)
        if not clues:
            return {"emoji_unavailable": True, "game": self.game, "game_mode": self.mode}

        session = PlaySessionService.get_or_create_from_context(
            self.user,
            self.game,
            play_context,
        )
        if session.emoji_clues_revealed < 1:
            session.emoji_clues_revealed = 1
            session.save(update_fields=["emoji_clues_revealed"])

        processor = EmojiGuessProcessor(self.game, self.mode, self.user)
        state = processor.build_state(session, play_context, clues)
        url_registry = PlayUrlRegistry(self.game, daily_target=self.daily_target)

        yesterday_target = TargetService(
            self.game,
            self.user,
            mode=self.mode,
        ).get_yesterday_target(today_date=self.daily_target.date)

        return {
            "game": self.game,
            "game_mode": self.mode,
            "daily_target": self.daily_target,
            "target": target_item,
            "emoji_state": state,
            "revealed_clues": state["revealed_clues"],
            "max_clues": state["max_clues"],
            "attempts": state["attempts"],
            "won": state["won"],
            "surrendered": state["surrendered"],
            "can_play": state["can_play"],
            "remaining_names_json": state["remaining_names_json"],
            "background_url": resolve_background_url(self.game, self.mode),
            "back_to_modes_url": reverse("play", args=[self.game.slug]),
            "guess_url": reverse("emoji_guess", args=[self.game.slug, self.mode.slug]),
            "surrender_url": url_registry.surrender_url(),
            "yesterday_target_name": (
                yesterday_target.target.name if yesterday_target else None
            ),
            **next_mode_navigation(self.game, self.user, self.mode),
        }
