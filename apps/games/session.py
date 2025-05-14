# apps/games/session.py
"""
Encapsula la gestión de la partida almacenada en sesión.
"""
import random
from typing import List

from .models import Game, GameItem

__all__ = ["GameSession"]


class GameSession:
    """Envuelve request.session para aislar la lógica de estado."""

    TARGET_ID = "target_id"
    TARGET_GAME = "target_game"
    GUESSES = "guesses"
    WON = "won"
    GUESS_ERROR = "guess_error"

    def __init__(self, session):
        self._s = session

    # ---------- getters ----------
    @property
    def target_id(self):
        return self._s.get(self.TARGET_ID)

    @property
    def target_game(self):
        return self._s.get(self.TARGET_GAME)

    @property
    def guess_ids(self) -> List[int]:
        return self._s.get(self.GUESSES, [])

    @property
    def won(self) -> bool:
        return self._s.get(self.WON, False)

    def pop_guess_error(self) -> bool:
        return self._s.pop(self.GUESS_ERROR, False)

    # ---------- mutators ----------
    def _set(self, **kwargs):
        self._s.update(kwargs)

    # ---------- public API ----------
    def start_new(self, game: Game) -> GameItem:
        target = random.choice(list(game.items.all()))
        self._set(
            target_id=target.id,
            target_game=game.id,
            guesses=[],
            won=False,
        )
        return target

    def add_guess(self, item: GameItem):
        ids = self.guess_ids + [item.id]
        self._set(guesses=ids)

    def flag_guess_error(self):
        self._s[self.GUESS_ERROR] = True

    def set_won(self):
        self._s[self.WON] = True
