import json

from apps.games.models import Game, GameAttempt, GameMode
from apps.games.services.catalog.item_pool_service import ItemPoolService
from apps.games.services.emoji.clue_service import EmojiClueService
from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.play_session_service import PlaySessionService


class EmojiGuessProcessor:
    def __init__(self, game: Game, mode: GameMode, user):
        self.game = game
        self.mode = mode
        self.user = user

    def process(self, request, daily_target) -> tuple[bool, dict]:
        play_context = PlayContext.exactly_one(daily_target=daily_target)
        target_item = play_context.target
        clues = EmojiClueService.get_clues(self.game, target_item)
        if not clues:
            return False, {"error": "Este personaje no tiene pistas emoji configuradas."}

        guess_name = request.POST.get("guess", "").strip()
        if not guess_name:
            return False, {"error": "Debes escribir un nombre."}

        guessed_item = (
            ItemPoolService(self.game, self.mode)
            .get_queryset()
            .filter(name__iexact=guess_name)
            .first()
        )
        if not guessed_item:
            return False, {"error": "Ese personaje no existe en este modo."}

        session = PlaySessionService.get_or_create_from_context(
            self.user,
            self.game,
            play_context,
        )
        if session.surrendered or GameAttempt.objects.filter(
            session=session, is_correct=True
        ).exists():
            return False, {"error": "La partida ya ha terminado."}

        if GameAttempt.objects.filter(session=session, guess=guessed_item).exists():
            return False, {"error": "Ese personaje ya fue usado."}

        is_correct = guessed_item.pk == target_item.pk
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            session=session,
            guess=guessed_item,
            is_correct=is_correct,
        )

        if not is_correct:
            session.emoji_clues_revealed = EmojiClueService.next_revealed_count(
                session.emoji_clues_revealed,
                len(clues),
            )
            session.save(update_fields=["emoji_clues_revealed"])

        return True, self.build_state(session, play_context, clues)

    def build_state(self, session, play_context, clues: list[str] | None = None) -> dict:
        target_item = play_context.target
        clues = clues if clues is not None else EmojiClueService.get_clues(self.game, target_item)
        attempts_query = session.attempts.select_related("guess").order_by("attempted_at")
        has_won = attempts_query.filter(is_correct=True).exists()
        can_play = not has_won and not session.surrendered

        guessed_item_ids = list(attempts_query.values_list("guess_id", flat=True))
        remaining_names = list(
            ItemPoolService(self.game, self.mode)
            .get_queryset()
            .exclude(id__in=guessed_item_ids)
            .values_list("name", flat=True)
        )

        return {
            "won": has_won,
            "can_play": can_play,
            "surrendered": session.surrendered,
            "target_name": target_item.name if (has_won or session.surrendered) else None,
            "revealed_clues": EmojiClueService.visible_clues(clues, session.emoji_clues_revealed),
            "max_clues": len(clues),
            "attempts": [
                {
                    "name": attempt.guess.name,
                    "is_correct": attempt.is_correct,
                    "guess_image_url": attempt.guess.get_image_url(),
                }
                for attempt in attempts_query
            ],
            "remaining_names": remaining_names,
            "remaining_names_json": json.dumps(remaining_names),
            "points_awarded": 0,
            "bet_amount": None,
            "global_average": None,
            "bet_won": None,
        }
