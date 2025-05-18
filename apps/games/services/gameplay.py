
import json
from apps.games.models import (
    DailyTarget,
    GameAttempt,
    GameResult
)
from apps.games.attempts import build_attempts


def get_current_target(game):
    """
    Devuelve la tupla (GameItem target, DailyTarget daily) para el día actual
    (hasta las 23:00), o para mañana si ya ha pasado la hora de corte.
    """
    daily = DailyTarget.get_current(game)
    return daily.target, daily


def process_guess(request, game, daily_target):
    """
    1) Valida que el nombre enviado exista en game.items y no se haya intentado ya hoy.
    2) Crea un GameAttempt.
    3) Si acierta, crea un GameResult (solo uno por user/daily_target).
       Devuelve (valido: bool, acierto: bool).
    """
    guess_name = request.POST.get("guess", "").strip()
    item = game.items.filter(name__iexact=guess_name).first()
    if not item:
        return False, False  # nombre inválido

    already = GameAttempt.objects.filter(
        user=request.user,
        daily_target=daily_target,
        guess=item
    ).exists()
    if already:
        return False, False  # repetido

    is_correct = (item.pk == daily_target.target.pk)
    GameAttempt.objects.create(
        user=request.user,
        game=game,
        daily_target=daily_target,
        guess=item,
        is_correct=is_correct
    )

    if is_correct:
        # Solo uno por día
        GameResult.objects.get_or_create(
            user=request.user,
            game=game,
            daily_target=daily_target,
            defaults={"attempts": GameAttempt.objects.filter(
                user=request.user,
                daily_target=daily_target
            ).count()}
        )

    return True, is_correct




def build_context(request, game, daily_target):
    # historial de intentos
    qs = GameAttempt.objects.filter(
        user=request.user,
        daily_target=daily_target
    ).order_by('-attempted_at')

    items     = [att.guess for att in qs]
    attempts  = build_attempts(game, items, daily_target.target)
    has_won   = qs.filter(is_correct=True).exists()
    can_play  = not has_won

    # Nombres restantes para el autocomplete
    # Excluimos los ya adivinados hoy
    guessed_ids = [att.guess.id for att in qs]
    remaining_names = list(
        game.items
            .exclude(id__in=guessed_ids)
            .values_list("name", flat=True)
    )
    remaining_names_json = json.dumps(remaining_names)

    return {
        "game":                  game,
        "target":                daily_target.target,
        "attempts":              attempts,
        "previous_guesses":      items,
        "won":                   has_won,
        "can_play":              can_play,
        "remaining_names_json":  remaining_names_json,
    }

