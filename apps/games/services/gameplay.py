# apps/games/services/gameplay.py
from typing import Tuple, List

from apps.games.models import Game, GameItem, GameResult
from apps.games.session import GameSession
from apps.games.attempts import build_attempts


# ---------- 1. procesa el POST ----------
def process_guess(request, game: Game, sess: GameSession, target: GameItem) -> None:
    """
    Valida el intento y actualiza la sesión / BBDD.
    Lanza ValueError si el intento es inválido.
    """
    guess_name = request.POST.get("guess", "").strip()
    guess = game.items.filter(name__iexact=guess_name).first()

    if not guess or guess.id in sess.guess_ids:
        sess.flag_guess_error()
        return

    sess.add_guess(guess)

    if guess.name == target.name:
        sess.set_won()
        GameResult.objects.create(
            user=request.user,
            game=game,
            attempts=len(sess.guess_ids),
        )


# ---------- 2. genera el contexto para la plantilla ----------
def build_context(game: Game, sess: GameSession, target: GameItem) -> dict:
    """
    Devuelve el dict que la plantilla necesita.
    Mantiene el orden 'último primero'.
    """
    ids: List[int] = sess.guess_ids
    items = list(GameItem.objects.filter(id__in=ids))
    items.sort(key=lambda g: ids.index(g.id), reverse=True)

    attempts = build_attempts(game, items, target)

    return {
        "game": game,
        "target": target,
        "attempts": attempts,
        "previous_guesses": items,
        "won": sess.won,
        "guess_error": sess.pop_guess_error(),
    }
