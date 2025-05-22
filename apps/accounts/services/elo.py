from __future__ import annotations

from django.db.models import Avg
from django.utils.timezone import now

from apps.accounts.models import GameElo
from apps.games.models import GameResult


class Elo:
    """Servicio de ELO por juego y usuario."""

    BASE_RATING = 1200

    # ---------- API pública ----------
    def __init__(self, user, game):
        self.user = user
        self.game = game
        self.elo_obj, _ = GameElo.objects.get_or_create(user=user, game=game)

    def update(self, attempts_this_game: int, k: int = 32) -> None:
        """Actualiza el rating tras la partida recién jugada."""
        self._add_played_game()

        if not self._has_historical_average():
            return                              # primerísima partida del juego

        result = self._did_win(attempts_this_game)
        opponent_rating = self._opponent_rating()

        if opponent_rating is None:             # todavía sin rivales
            return

        self._apply_elo_change(result, opponent_rating, k)
    # ----------------------------------

    # ---------- Métodos privados (SRP) ----------
    def _add_played_game(self) -> None:
        """Incrementa el contador de partidas y guarda."""
        self.elo_obj.partidas += 1
        self.elo_obj.save(update_fields=("partidas",))

    # -- regla 1: media histórica previa --
    def _historical_average(self) -> float | None:
        return (
            GameResult.objects
            .filter(game=self.game, completed_at__lt=now())
            .aggregate(avg=Avg("attempts"))["avg"]
        )

    def _has_historical_average(self) -> bool:
        return self._historical_average() is not None

    # -- regla 2: victoria / derrota --
    def _did_win(self, attempts_this_game: int) -> int:
        return 1 if attempts_this_game < self._historical_average() else 0

    # -- regla 3: rival válido --
    def _other_elos(self) -> list[float]:
        return list(
            GameElo.objects
            .filter(game=self.game)
            .exclude(user=self.user)
            .exclude(partidas=0)
            .values_list("elo", flat=True)
        )

    def _opponent_rating(self) -> float | None:
        others = self._other_elos()
        return sum(others) / len(others) if others else None

    # -- regla 4: fórmula Elo --
    @staticmethod
    def _expected(player_rating: float, opponent_rating: float) -> float:
        return 1 / (1 + 10 ** ((opponent_rating - player_rating) / 400))

    def _apply_elo_change(self, result: int, opponent_rating: float, k: int) -> None:
        expected = self._expected(self.elo_obj.elo, opponent_rating)
        self.elo_obj.elo += k * (result - expected)
        self.elo_obj.save(update_fields=("elo",))
    # -------------------------------------------
