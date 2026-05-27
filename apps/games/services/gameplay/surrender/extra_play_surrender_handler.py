from apps.accounts.services.score_service import ScoreService
from apps.games.models import GameAttempt


class ExtraPlaySurrenderHandler:
    def __init__(self, user, game):
        self.user = user
        self.game = game

    def apply(self, play_session, extra_play):
        self._complete_extra_play(extra_play)
        return self._build_lost_bet_points_data(play_session, extra_play)

    def _complete_extra_play(self, extra_play):
        if extra_play.completed:
            return

        extra_play.completed = True
        extra_play.save(update_fields=["completed"])

    def _build_lost_bet_points_data(self, play_session, extra_play):
        attempts_count = GameAttempt.objects.filter(session=play_session).count()
        score_service = ScoreService(self.user, self.game, mode=extra_play.mode)
        global_average = score_service.calculate_global_average_of_averages(exclude_user=True)
        if global_average is None:
            global_average = score_service.calculate_user_average_attempts()

        return {
            "points_awarded": 0,
            "bet_amount": extra_play.bet_amount,
            "net_profit": 0,
            "global_average": global_average,
            "current_attempts": attempts_count,
            "bet_won": False,
        }
