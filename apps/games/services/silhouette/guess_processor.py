import json

from apps.games.models import Game, GameAttempt, GameMode, SilhouetteDailyAssignment
from apps.games.services.silhouette.pool_service import SilhouettePoolService
from apps.games.services.silhouette.session_service import SilhouetteSessionService


class SilhouetteGuessProcessor:
    def __init__(self, game: Game, mode: GameMode, user):
        self.game = game
        self.mode = mode
        self.user = user

    def process(
        self, request, assignment: SilhouetteDailyAssignment
    ) -> tuple[bool, dict]:
        session = SilhouetteSessionService.get_or_create(
            self.user, self.game, self.mode, assignment
        )
        finished, payload = self._reject_if_finished(session)
        if finished:
            return False, payload

        guess_name = request.POST.get("guess", "").strip()
        if not guess_name:
            return False, {"error": "Debes escribir un nombre."}

        pool = SilhouettePoolService(self.game, self.mode, assignment.filter_config)
        pool_queryset = pool.item_queryset()

        guessed_item = pool_queryset.filter(name__iexact=guess_name).first()
        if not guessed_item:
            return False, {"error": "Ese Pokémon no existe en este modo."}

        if GameAttempt.objects.filter(session=session, guess=guessed_item).exists():
            return False, {"error": "Ese Pokémon ya fue usado."}

        target_item = assignment.target_item
        is_correct = guessed_item.pk == target_item.pk
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            session=session,
            guess=guessed_item,
            is_correct=is_correct,
        )

        return True, self.build_state(session, assignment)

    def surrender(self, assignment: SilhouetteDailyAssignment) -> dict:
        session = SilhouetteSessionService.get_or_create(
            self.user, self.game, self.mode, assignment
        )
        if session.surrendered or GameAttempt.objects.filter(
            session=session, is_correct=True
        ).exists():
            raise ValueError("La partida ya ha terminado.")

        session.surrendered = True
        session.save(update_fields=["surrendered"])
        return self.build_state(session, assignment)

    def _reject_if_finished(self, session) -> tuple[bool, dict | None]:
        if session.surrendered:
            return True, {"error": "La partida ya ha terminado."}
        if GameAttempt.objects.filter(session=session, is_correct=True).exists():
            return True, {"error": "La partida ya ha terminado."}
        return False, None

    def build_state(self, session, assignment: SilhouetteDailyAssignment) -> dict:
        target_item = assignment.target_item
        attempts_query = session.attempts.select_related("guess").order_by("attempted_at")
        has_won = attempts_query.filter(is_correct=True).exists()
        can_play = not has_won and not session.surrendered
        wrong_attempts = attempts_query.filter(is_correct=False).count()

        guessed_item_ids = list(attempts_query.values_list("guess_id", flat=True))
        pool_queryset = SilhouettePoolService(
            self.game, self.mode, assignment.filter_config
        ).item_queryset()
        remaining_names = list(
            pool_queryset.exclude(id__in=guessed_item_ids).values_list("name", flat=True)
        )

        image_url = target_item.get_image_url()
        return {
            "won": has_won,
            "can_play": can_play,
            "surrendered": session.surrendered,
            "target_name": target_item.name if (has_won or session.surrendered) else None,
            "target_image_url": image_url if (has_won or session.surrendered) else None,
            "zoom_level": wrong_attempts,
            "anchor": assignment.anchor,
            "sprite_url": image_url,
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
        }
