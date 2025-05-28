
import json

from django.db.models import Avg

from apps.accounts.models import Challenge
from apps.accounts.services.elo import Elo
from apps.games.models import (
    DailyTarget,
    GameAttempt,
    GameResult, GameItem, Game
)
from apps.games.attempts import build_attempts


import random

def get_random_item(game):
    """
    Retorna un GameItem aleatorio asociado a un juego específico.
    """
    return random.choice(list(game.items.all()))

def get_current_target(game, user):
    """
    Devuelve la tupla (GameItem target, DailyTarget daily) para el día actual
    (hasta las 23:00), o para mañana si ya ha pasado la hora de corte.
    """
    daily = DailyTarget.get_current(game, user)
    if not daily or not daily.target:
        return None, None
    return daily.target, daily


def process_guess(
    request,
    game,
    *,
    daily_target: DailyTarget | None = None,
    challenge: Challenge | None = None,
):
    """
    Registra un intento y devuelve (valid, correct).

    - daily_target → partida diaria
    - challenge    → reto 1v1
    """
    if daily_target is None and challenge is None:
        raise ValueError("Debes indicar daily_target o challenge.")

    guess_name = request.POST.get("guess", "").strip()
    item = game.items.filter(name__iexact=guess_name).first()
    if not item:
        return False, False

    # ---------- Partida diaria ----------
    if daily_target is not None:
        already = GameAttempt.objects.filter(
            user=request.user,
            daily_target=daily_target,
            guess=item,
        ).exists()
        if already:
            return False, False

        is_correct = item.pk == daily_target.target_id
        attempt = GameAttempt.objects.create(
            user=request.user,
            game=game,
            daily_target=daily_target,
            guess=item,
            is_correct=is_correct,
        )

    # ---------- Reto ----------
    else:
        already = GameAttempt.objects.filter(
            user=request.user,
            challenge=challenge,
            guess=item,
        ).exists()
        if already:
            return False, False

        is_correct = item.pk == challenge.target_id
        attempt = GameAttempt.objects.create(
            user=request.user,
            game=game,
            challenge=challenge,
            guess=item,
            is_correct=is_correct,
        )

    # Si es correcto y estamos en daily → ELO, etc. (dejamos tu lógica intacta)
    if is_correct and daily_target is not None:
        from apps.accounts.services.elo import Elo
        result, created = GameResult.objects.get_or_create(
            user=request.user,
            game=game,
            daily_target=daily_target,
            defaults={
                "attempts": GameAttempt.objects.filter(
                    user=request.user,
                    daily_target=daily_target,
                ).count()
            },
        )
        if created:
            Elo(request.user, game).update(result.attempts)

    return True, is_correct



def build_context(
    request,
    game,
    *,
    daily_target: DailyTarget | None = None,
    challenge: Challenge | None = None,
) -> dict:
    """
    Construye el contexto del juego.

    - daily_target → partida diaria
    - challenge    → reto 1 v 1
    """
    if daily_target is None and challenge is None:
        raise ValueError("Debes indicar daily_target o challenge.")

    # ---------- 1) Partida diaria ----------
    if daily_target is not None:
        qs = GameAttempt.objects.filter(
            user=request.user,
            daily_target=daily_target,
        ).order_by("-attempted_at")
        target_item = daily_target.target

    # ---------- 2) Reto 1 v 1 ----------
    else:
        qs = GameAttempt.objects.filter(
            user=request.user,
            challenge=challenge,
        ).order_by("-attempted_at")
        target_item = challenge.target

    # ---------- resto común ----------
    items = [att.guess for att in qs]
    attempts = build_attempts(game, items, target_item)
    has_won = qs.filter(is_correct=True).exists()
    can_play = not has_won

    guessed_ids = [att.guess_id for att in qs]
    remaining_names = list(
        game.items.exclude(id__in=guessed_ids).values_list("name", flat=True)
    )

    return {
        "game": game,
        "target": target_item,
        "attempts": attempts,
        "previous_guesses": items,
        "won": has_won,
        "can_play": can_play,
        "remaining_names_json": json.dumps(remaining_names),
    }






