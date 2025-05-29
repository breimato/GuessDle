from django.db.models import Q
from apps.games.models import GameAttempt
from .result_updater import ResultUpdater


class GuessProcessor:
    def __init__(self, game, user):
        self.game = game
        self.user = user

    def process(self, request, *, daily_target=None, challenge=None):
        if not daily_target and not challenge:
            raise ValueError("Debes indicar daily_target o challenge.")

        guess_name = request.POST.get("guess", "").strip()
        item = self.game.items.filter(name__iexact=guess_name).first()
        if not item:
            return False, False

        # Evitar intentos duplicados
        filter_kwargs = Q(user=self.user, guess=item)
        if daily_target:
            filter_kwargs &= Q(daily_target=daily_target)
            target_id = daily_target.target_id
        else:
            filter_kwargs &= Q(challenge=challenge)
            target_id = challenge.target_id

        if GameAttempt.objects.filter(filter_kwargs).exists():
            return False, False

        is_correct = item.pk == target_id
        GameAttempt.objects.create(
            user=self.user,
            game=self.game,
            guess=item,
            is_correct=is_correct,
            daily_target=daily_target,
            challenge=challenge,
        )

        # Delegar al updater si es correcto
        if is_correct and daily_target:
            ResultUpdater(self.game, self.user).update_for_daily(daily_target)

        return True, is_correct
