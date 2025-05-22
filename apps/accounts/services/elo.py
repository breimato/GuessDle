from django.db.models import Avg
from apps.accounts.models import GameElo
from apps.games.models import GameResult
from django.utils.timezone import now



class Elo:
    """
    Servicio de ELO por juego y usuario.
    Solo actualiza cuando hay, al menos, otro jugador con partidas en ese juego.
    """

    BASE_RATING = 1200          # Puntos iniciales / rival virtual de respaldo

    def __init__(self, user, game):
        self.user = user
        self.game = game
        self.elo_obj, _ = GameElo.objects.get_or_create(user=user, game=game)

    # ------------  Fórmula básica ------------
    @staticmethod
    def _expected(player_rating, opponent_rating):
        return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))
    # -----------------------------------------

    def update(self, attempts_this_game: int, k: int = 32) -> None:
        """
        Llamar después de crear el GameResult de la partida recién jugada.

        · Cuenta SIEMPRE la partida (`partidas += 1`)
        · Si eres el primer jugador del juego → solo suma la partida (rating intacto)
        · Si ya hay media histórica pero aún no hay rivales → solo suma la partida
        · Cuando hay rivales con al menos 1 partida, ajusta el Elo
        """

        # 1) Registrar la partida SIEMPRE
        self.elo_obj.partidas += 1

        # 2) Media histórica previa (sin esta partida)
        prev_avg = (
            GameResult.objects
            .filter(game=self.game, completed_at__lt=now())
            .aggregate(avg=Avg("attempts"))["avg"]
        )
        if prev_avg is None:
            # Primera partida absoluta del juego: no hay referencia
            self.elo_obj.save()
            return

        # 3) ¿Ganó? (menos intentos que la media histórica)
        result = 1 if attempts_this_game < prev_avg else 0

        # 4) Elo medio de los demás jugadores con ≥1 partida
        other_elos = (
            GameElo.objects
            .filter(game=self.game)
            .exclude(user=self.user)
            .exclude(partidas=0)
            .values_list("elo", flat=True)
        )

        if not other_elos:
            # No hay rival aún ⇒ solo guardamos partidas
            self.elo_obj.save()
            return

        opponent_rating = sum(other_elos) / len(other_elos)

        # 5) Ajustar Elo
        expected = self._expected(self.elo_obj.elo, opponent_rating)
        new_rating = self.elo_obj.elo + k * (result - expected)

        self.elo_obj.elo = new_rating
        self.elo_obj.save()

    # ---------- ELO global del usuario ----------
    @staticmethod
    def global_elo_for_user(user):
        records = GameElo.objects.filter(user=user)
        total_games = sum(r.partidas for r in records)
        if total_games == 0:
            return 1200
        weighted = sum(r.elo * r.partidas for r in records)
        return weighted / total_games
