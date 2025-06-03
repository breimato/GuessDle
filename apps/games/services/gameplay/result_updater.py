# apps/games/services/gameplay/result_updater.py

from django.db.models import Count
from apps.games.models import ExtraDailyPlay, GameAttempt
from apps.games.services.gameplay.challenger_manager import ChallengeManager
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.accounts.services.score_service import ScoreService


class ResultUpdater:
    def __init__(self, game, user):
        self.game = game
        self.user = user

    def update_for_game(self, *, daily_target=None, extra_play=None, challenge=None):
        contexts = [daily_target, extra_play, challenge]
        if sum(bool(x) for x in contexts) != 1:
            raise ValueError("Debes indicar exactamente un contexto (daily, extra o challenge).")

        # Creamos o recuperamos la PlaySession
        session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        # Contamos cuántos intentos hubo en esa sesión
        attempts_count = GameAttempt.objects.filter(session=session).count()

        # 1️⃣ CONTEXTO DAILY
        if daily_target:
            score_service = ScoreService(self.user, self.game)
            return score_service.add_points_for_attempts(attempts_count)

        # 2️⃣ CONTEXTO EXTRA
        if extra_play:
            bet_amount = ExtraDailyPlay.objects.get(pk=extra_play.id, user=self.user).bet_amount
            score_service = ScoreService(self.user, self.game)

            global_avg = score_service.get_global_average_of_averages(exclude_user=True)

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

        # 3️⃣ CONTEXTO CHALLENGE
        if challenge:
            if not challenge.completed:
                manager = ChallengeManager(user=self.user, challenge=challenge)
                manager.calculate_winner()

            if not challenge.winner:
                manager = ChallengeManager(user=self.user, challenge=challenge)
                tied_users = manager.get_tied_users()

                total_points = 0
                for user in tied_users:
                    session = PlaySessionService.get_or_create(user, self.game, challenge=challenge)
                    attempts = GameAttempt.objects.filter(session=session).count()
                    score_service = ScoreService(user, self.game)
                    base_pts = score_service.add_points_for_attempts(attempts)
                    total_points += base_pts  # Solo por si quieres devolver el total

                return total_points  # O puedes retornar lo de self.user si solo importa eso

            if challenge.points_assigned:
                return 0

            # — Aquí ya hay winner y points_assigned=False: asignamos base + bonus
            ganador = challenge.winner
            session_winner = PlaySessionService.get_or_create(
                ganador,
                self.game,
                challenge=challenge
            )
            attempts_winner = GameAttempt.objects.filter(session=session_winner).count()
            score_service = ScoreService(ganador, self.game)
            base_pts = score_service.add_points_for_attempts(attempts_winner)
            score_service.score_obj.elo += 100
            score_service.score_obj.save(update_fields=("elo",))
            challenge.points_assigned = True
            challenge.save(update_fields=["points_assigned"])
            return base_pts + 100

