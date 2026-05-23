"""Service to validate and process guess attempts, register attempts, and trigger outcome score updates."""

from apps.games.models import GameAttempt
from apps.accounts.services.score_service import ScoreService
from .result_updater import ResultUpdater
from .play_session_service import PlaySessionService


class GuessProcessor:
    """Handles verification of new guesses, checks for duplication, stores attempts, and updates game results."""

    def __init__(self, game, user):
        """Initialize guess processor."""

        self.game = game
        self.user = user

    def process(self, request, *, daily_target=None, extra_play=None, challenge=None):
        """Validate, store, and process a user's guess, returning a tuple (is_valid, is_correct, points_data)."""

        if sum(bool(param) for param in (daily_target, extra_play, challenge)) != 1:
            raise ValueError("Must specify exactly one of daily_target, challenge, or extra_play.")

        guess_name = request.POST.get("guess", "").strip()
        guessed_item = self.game.items.filter(name__iexact=guess_name).first()
        if not guessed_item:
            return False, False, {}

        play_session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        if GameAttempt.objects.filter(session=play_session, guess=guessed_item).exists():
            return False, False, {}

        if daily_target:
            target_item = daily_target.target
        elif extra_play:
            target_item = extra_play.target
        else:
            target_item = challenge.target

        is_correct = guessed_item.pk == target_item.pk

        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            session=play_session,
            guess=guessed_item,
            is_correct=is_correct
        )

        points_data = {}
        if is_correct:
            points_data = ResultUpdater(self.game, self.user).update_for_game(
                daily_target=daily_target,
                extra_play=extra_play,
                challenge=challenge,
            )
        else:
            attempts_count = GameAttempt.objects.filter(session=play_session).count()
            if extra_play:
                score_service = ScoreService(self.user, self.game)
                global_average = score_service.calculate_global_average_of_averages(exclude_user=True)
                if global_average is None:
                    global_average = score_service.calculate_user_average_attempts()
                if (
                    global_average is not None
                    and float(attempts_count) >= float(global_average)
                    and not extra_play.completed
                ):
                    extra_play.completed = True
                    extra_play.save(update_fields=["completed"])
                points_data = {
                    "points_awarded": 0,
                    "bet_amount": extra_play.bet_amount,
                    "net_profit": 0,
                    "global_average": global_average,
                    "current_attempts": attempts_count,
                    "bet_won": False,
                }
            else:
                points_data = {
                    "points_awarded": 0,
                    "bet_amount": None,
                    "global_average": None,
                    "current_attempts": attempts_count,
                    "bet_won": None,
                }

        return True, is_correct, points_data
