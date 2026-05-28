from apps.games.services.play_session.outcome_registry import resolve_outcome
from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.play_kind import PlayKind
from apps.games.models import GameAttempt
from apps.games.services.catalog.item_pool_service import ItemPoolService
from apps.games.services.extra.session import mark_extra_play_lost_if_over_average
from apps.games.services.play_session.play_session_service import PlaySessionService


class GuessProcessor:

    def __init__(self, game, user):
        self.game = game
        self.user = user

    def process(self, request, *, daily_target=None, extra_play=None, challenge=None):
        play_context = PlayContext.exactly_one(
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        guess_name = request.POST.get("guess", "").strip()
        guessed_item = (
            ItemPoolService(self.game, play_context.mode)
            .get_queryset()
            .filter(name__iexact=guess_name)
            .first()
        )
        if not guessed_item:
            return False, False, {}

        play_session = PlaySessionService.get_or_create_from_context(
            self.user,
            self.game,
            play_context,
        )
        if GameAttempt.objects.filter(session=play_session, guess=guessed_item).exists():
            return False, False, {}

        target_item = play_context.target
        is_correct = guessed_item.pk == target_item.pk

        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            session=play_session,
            guess=guessed_item,
            is_correct=is_correct,
        )

        if is_correct:
            points_data = resolve_outcome(self.game, self.user, play_context)
            return True, True, points_data

        attempts_count = GameAttempt.objects.filter(session=play_session).count()
        if play_context.kind == PlayKind.EXTRA:
            return True, False, mark_extra_play_lost_if_over_average(
                play_context.extra_play, attempts_count
            )

        return True, False, self._build_non_extra_miss_payload(attempts_count)

    @staticmethod
    def _build_non_extra_miss_payload(attempts_count: int) -> dict:
        return {
            "points_awarded": 0,
            "bet_amount": None,
            "global_average": None,
            "current_attempts": attempts_count,
            "bet_won": None,
        }
