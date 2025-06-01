# apps/games/services/gameplay/guess_processor.py
from django.db.models import Q
from apps.games.models import GameAttempt
from .result_updater import ResultUpdater
from .play_session_service import PlaySessionService


class GuessProcessor:
    """Procesa un intento: valida duplicados, guarda intento y actualiza resultado."""

    def __init__(self, game, user):
        self.game = game
        self.user = user

    # daily_target / extra_play / challenge son mutuamente excluyentes
    def process(self, request, *, daily_target=None, extra_play=None, challenge=None):
        if sum(bool(x) for x in (daily_target, extra_play, challenge)) != 1:
            raise ValueError("Debes indicar daily_target, challenge o extra_play.")

        guess_name = request.POST.get("guess", "").strip()
        item = self.game.items.filter(name__iexact=guess_name).first()
        if not item:
            return False, False  # nombre incorrecto

        # -------------------- 1️⃣ Sesión -------------------- #
        session = PlaySessionService.get_or_create(
            self.user,
            self.game,
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )

        # -------------------- 2️⃣ Duplicados -------------------- #
        if GameAttempt.objects.filter(session=session, guess=item).exists():
            return False, False

        # -------------------- 3️⃣ ¿Es correcto? ----------------- #
        if daily_target:
            target_item = daily_target.target
        elif extra_play:
            target_item = extra_play.target
        else:  # challenge
            target_item = challenge.target

        is_correct = item.pk == target_item.pk

        # -------------------- 4️⃣ Guardar intento --------------- #
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            session=session,
            guess=item,
            is_correct=is_correct,
            # dejamos los FK antiguos para retro-compatibilidad
            daily_target=daily_target,
            challenge=challenge,
            extra_play=extra_play,
        )

        # -------------------- 5️⃣ Actualizar resultado ---------- #
        if is_correct:
            ResultUpdater(self.game, self.user).update_for_game(
                daily_target=daily_target,
                extra_play=extra_play,
                challenge=challenge,
            )

        return True, is_correct
