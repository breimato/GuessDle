"""Service to update scores and assign points/bonuses depending on the game play mode."""

from apps.games.models import ExtraDailyPlay, GameAttempt
from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.accounts.services.score_service import ScoreService


class ResultUpdater:
    """Updates points for daily target wins, extra daily wagering play sessions, and 1v1 challenges."""

    def __init__(self, game, user):
        """Initialize result updater."""

        self.game = game
        self.user = user

    BET_MULTIPLIER = 1.5
    CHALLENGE_WINNER_BONUS = 100

    def update_for_game(self, *, daily_target=None, extra_play=None, challenge=None):
        """Calculate and update point balances, saving Elo additions for the active game session."""

        contexts = [daily_target, extra_play, challenge]
        if sum(bool(param) for param in contexts) != 1:
            raise ValueError("Must specify exactly one context (daily, extra, or challenge).")

        play_session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        attempts_count = GameAttempt.objects.filter(session=play_session).count()

        if daily_target:
            score_service = ScoreService(self.user, self.game)
            points_awarded = score_service.add_points_for_attempts(attempts_count)
            return {
                "points_awarded": points_awarded,
                "bet_amount": None,
                "global_average": None,
                "current_attempts": attempts_count,
                "bet_won": None,
            }

        if extra_play:
            bet_amount = ExtraDailyPlay.objects.get(pk=extra_play.id, user=self.user).bet_amount
            score_service = ScoreService(self.user, self.game)
            global_average = score_service.calculate_global_average_of_averages(exclude_user=True)

            if global_average is not None:
                has_beaten_average = float(attempts_count) < float(global_average)
            else:
                user_average = score_service.calculate_user_average_attempts()
                has_beaten_average = (
                    user_average is None or float(attempts_count) < float(user_average)
                )

            bonus_points = bet_amount * self.BET_MULTIPLIER if has_beaten_average else 0
            net_profit = bonus_points - bet_amount if has_beaten_average else 0
            if bonus_points:
                score_service.score_obj.elo += bonus_points
                score_service.score_obj.save(update_fields=("elo",))

            if not extra_play.completed:
                extra_play.completed = True
                extra_play.save(update_fields=["completed"])

            active_average = global_average if global_average is not None else score_service.calculate_user_average_attempts()

            return {
                "points_awarded": bonus_points,
                "bet_amount": bet_amount,
                "net_profit": net_profit,
                "global_average": active_average,
                "current_attempts": attempts_count,
                "bet_won": has_beaten_average,
            }

        if challenge:
            if not challenge.completed:
                challenge_manager = ChallengeManager(user=self.user, challenge=challenge)
                challenge_manager.calculate_winner()

            if not challenge.winner:
                challenge_manager = ChallengeManager(user=self.user, challenge=challenge)
                tied_users = challenge_manager.get_tied_users()
                total_points = 0
                for tied_user in tied_users:
                    user_session = PlaySessionService.get_or_create(tied_user, self.game, challenge=challenge)
                    tied_user_attempts = GameAttempt.objects.filter(session=user_session).count()
                    score_service = ScoreService(tied_user, self.game)
                    base_points = score_service.add_points_for_attempts(tied_user_attempts)
                    total_points += base_points

                return {
                    "points_awarded": total_points,
                    "bet_amount": None,
                    "global_average": None,
                    "current_attempts": attempts_count,
                    "bet_won": None,
                }

            if challenge.points_assigned:
                return {
                    "points_awarded": 0,
                    "bet_amount": None,
                    "global_average": None,
                    "current_attempts": attempts_count,
                    "bet_won": None,
                }

            winner = challenge.winner
            winner_play_session = PlaySessionService.get_or_create(
                winner,
                self.game,
                challenge=challenge
            )
            winner_attempts_count = GameAttempt.objects.filter(session=winner_play_session).count()
            score_service = ScoreService(winner, self.game)
            base_points = score_service.add_points_for_attempts(winner_attempts_count)
            score_service.score_obj.elo += self.CHALLENGE_WINNER_BONUS
            score_service.score_obj.save(update_fields=("elo",))
            challenge.points_assigned = True
            challenge.save(update_fields=["points_assigned"])
            return {
                "points_awarded": base_points + self.CHALLENGE_WINNER_BONUS,
                "bet_amount": None,
                "global_average": None,
                "current_attempts": attempts_count,
                "bet_won": None,
            }
