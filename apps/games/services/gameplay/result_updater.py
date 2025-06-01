from apps.games.models import ExtraDailyPlay, GameAttempt, GameResult
from apps.accounts.services.elo import Elo
from django.db.models import Q, Avg

class ResultUpdater:
    def __init__(self, game, user):
        self.game = game
        self.user = user

    def update_for_game(self, *, daily_target=None, extra_play=None, challenge=None, bet_amount=None):
        filter_kwargs = {
            "user": self.user,
            "game": self.game,
            "daily_target": daily_target,
            "extra_play": extra_play,
            "challenge": challenge,
        }

        # Filtrar solo con valores no nulos
        filtered_kwargs = {k: v for k, v in filter_kwargs.items() if v}

        attempts_qs = GameAttempt.objects.filter(**filtered_kwargs)
        attempts_count = attempts_qs.count()

        result, created = GameResult.objects.get_or_create(
            **filtered_kwargs,
            defaults={"attempts": attempts_count},
        )

        if not created:
            return

        elo_service = Elo(self.user, self.game)

        if extra_play:
            bet_amount = ExtraDailyPlay.objects.filter(pk=extra_play.id, user=self.user).get().bet_amount

            # 👉 Verificar si hay otros jugadores en el juego
            hay_otros = GameResult.objects.filter(game=self.game).exclude(user=self.user).exists()
            if hay_otros:
                # Calculamos si ganó comparando con media global
                result_flag = elo_service._did_win(attempts_count)
            else:
                # Solo se compara consigo mismo
                user_avg = (
                    GameResult.objects
                    .filter(game=self.game, user=self.user)
                    .aggregate(avg=Avg("attempts"))["avg"]
                )
                result_flag = 1 if user_avg is None or attempts_count < user_avg else 0

            # Aplicamos resultado manual
            gain = bet_amount * (1.5 if result_flag == 1 else 0)
            elo_service.elo_obj.elo += gain
            elo_service.elo_obj.partidas += 1
            elo_service.elo_obj.save(update_fields=["elo", "partidas"])
        else:
            # Flujo normal de ELO
            elo_service.update(attempts_count)
