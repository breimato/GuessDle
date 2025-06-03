# apps/games/services/gameplay/result_updater.py

from django.db.models import Count
from apps.games.models import ExtraDailyPlay, GameAttempt
from .challenger_manager import ChallengeManager
from .play_session_service import PlaySessionService
from apps.accounts.services.score_service import ScoreService


class ResultUpdater:
    def __init__(self, game, user):
        self.game = game
        self.user = user

    def update_for_game(self, *, daily_target=None, extra_play=None, challenge=None):
        contexts = [daily_target, extra_play, challenge]
        if sum(bool(x) for x in contexts) != 1:
            raise ValueError("Debes indicar exactamente un contexto (daily, extra o challenge).")

        session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        attempts_count = GameAttempt.objects.filter(session=session).count()

        # 🎯 DAILY
        if daily_target:
            score_service = ScoreService(self.user, self.game)
            return score_service.add_points_for_attempts(attempts_count)

        # 🎰 EXTRA
        if extra_play:
            bet_amount = ExtraDailyPlay.objects.get(pk=extra_play.id, user=self.user).bet_amount
            score_service = ScoreService(self.user, self.game)

            global_avg = score_service.get_global_average_attempts(exclude_user=True)

            if global_avg is not None:
                result_flag = attempts_count < global_avg
            else:
                user_avg = score_service.get_user_average_attempts()
                result_flag = True if user_avg is None or attempts_count < user_avg else False

            bonus_pts = bet_amount * 1.5 if result_flag else 0

            if bonus_pts:
                score_service.score_obj.elo += bonus_pts
                score_service.score_obj.save(update_fields=("elo",))

            return bonus_pts

        # 🏆 CHALLENGE
        if challenge:
            # 1️⃣ Puntos base por intentos propios
            score_service = ScoreService(self.user, self.game)
            base_pts = score_service.add_points_for_attempts(attempts_count)

            # 2️⃣ Calcular ganador
            manager = ChallengeManager(user=self.user, challenge=challenge)
            won_challenge = manager.calculate_winner()

            # 3️⃣ Bonus si ganó el reto
            bonus_pts = 100 if won_challenge else 0
            if bonus_pts:
                score_service.score_obj.elo += bonus_pts
                score_service.score_obj.save(update_fields=("elo",))

            return base_pts + bonus_pts

