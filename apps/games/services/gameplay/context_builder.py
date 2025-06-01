# apps/games/services/gameplay/context_builder.py

import json
from apps.games.attempts import build_attempts
from apps.games.models import GameAttempt
from .play_session_service import PlaySessionService
from .target_service import TargetService


class ContextBuilder:
    def __init__(self, request, game, daily_target=None, challenge=None, extra_play=None):
        if daily_target is None and challenge is None and extra_play is None:
            raise ValueError("Debes indicar daily_target o challenge o extra.")
        
        self.request = request
        self.game = game
        self.daily_target = daily_target
        self.challenge = challenge
        self.extra_play = extra_play

    def build(self):
        if self.extra_play:
            session = PlaySessionService.get_or_create(
                self.request.user, self.game, extra_play=self.extra_play
            )
            target_item = self.extra_play.target
        elif self.daily_target:
            session = PlaySessionService.get_or_create(
                self.request.user, self.game, daily_target=self.daily_target
            )
            target_item = self.daily_target.target
        else:  # challenge
            session = PlaySessionService.get_or_create(
                self.request.user, self.game, challenge=self.challenge
            )
            target_item = self.challenge.target

        qs = GameAttempt.objects.filter(session=session).order_by("-attempted_at")

        attempts = build_attempts(self.game,[att.guess for att in qs],target_item)

        has_won = qs.filter(is_correct=True).exists()
        can_play = not has_won

        guessed_ids = [att.guess_id for att in qs]
        remaining_names = list(self.game.items.exclude(id__in=guessed_ids).values_list("name", flat=True))

        ctx = {
            "game": self.game,
            "target": target_item,
            "attempts": attempts,
            "previous_guesses": [att.guess for att in qs],
            "won": has_won,
            "can_play": can_play,
            "remaining_names_json": json.dumps(remaining_names),
        }

        if self.daily_target or self.extra_play:
            ctx["guess_url"] = self._get_guess_url()
            ctx["background_url"] = self.game.background_image.url if self.game.background_image else None

            if self.daily_target:
                yesterday_target = TargetService(self.game, self.request.user).get_yesterday_target(
                    today_date=self.daily_target.date)
                if yesterday_target:
                    ctx["yesterday_target_name"] = yesterday_target.target.name

        return ctx

    def _get_guess_url(self):
        from django.urls import reverse
        return reverse("ajax_guess", args=[self.game.slug])
