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
            return score_service.add_points_for_attempts(attempts_count)

        if extra_play:
            bet_amount = ExtraDailyPlay.objects.get(pk=extra_play.id, user=self.user).bet_amount
            score_service = ScoreService(self.user, self.game)

            global_average = score_service.calculate_global_average_of_averages(exclude_user=True)

            if global_average is not None:
                has_beaten_average = attempts_count < global_average
            else:
                user_average = score_service.calculate_user_average_attempts()
                has_beaten_average = user_average is None or attempts_count < user_average

            bonus_points = bet_amount * 1.5 if has_beaten_average else 0
            if bonus_points:
                score_service.score_obj.elo += bonus_points
                score_service.score_obj.save(update_fields=("elo",))
            return bonus_points

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

                return total_points

            if challenge.points_assigned:
                return 0

            winner = challenge.winner
            winner_play_session = PlaySessionService.get_or_create(
                winner,
                self.game,
                challenge=challenge
            )
            winner_attempts_count = GameAttempt.objects.filter(session=winner_play_session).count()
            score_service = ScoreService(winner, self.game)
            base_points = score_service.add_points_for_attempts(winner_attempts_count)
            score_service.score_obj.elo += 100
            score_service.score_obj.save(update_fields=("elo",))
            challenge.points_assigned = True
            challenge.save(update_fields=["points_assigned"])
            return base_points + 100
