"""Service to construct the templates rendering context for active play sessions."""

import json
from django.urls import reverse

from apps.games.attempts import build_attempts
from apps.games.models import GameAttempt
from .play_session_service import PlaySessionService
from .target_service import TargetService


class ContextBuilder:
    """Builds rendering context for the play pages, including attempts list, state, and autocomplete options."""

    def __init__(self, request, game, daily_target=None, challenge=None, extra_play=None):
        """Initialize context builder."""

        if daily_target is None and challenge is None and extra_play is None:
            raise ValueError("Must specify daily_target, challenge, or extra_play.")

        self.request = request
        self.game = game
        self.daily_target = daily_target
        self.challenge = challenge
        self.extra_play = extra_play

    def build(self):
        """Generate a dictionary containing the game state, previous attempts, and target configurations."""

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
        else:
            session = PlaySessionService.get_or_create(
                self.request.user, self.game, challenge=self.challenge
            )
            target_item = self.challenge.target

        attempts_query = GameAttempt.objects.filter(session=session).order_by("-attempted_at")

        attempts = build_attempts(self.game, [attempt.guess for attempt in attempts_query], target_item)

        has_won = attempts_query.filter(is_correct=True).exists()
        can_play = not has_won

        guessed_item_ids = [attempt.guess_id for attempt in attempts_query]
        remaining_names = list(
            self.game.items.filter(deleted=False).exclude(id__in=guessed_item_ids).values_list("name", flat=True)
        )
        context = {
            "game": self.game,
            "target": target_item,
            "attempts": attempts,
            "previous_guesses": [attempt.guess for attempt in attempts_query],
            "won": has_won,
            "can_play": can_play,
            "remaining_names_json": json.dumps(remaining_names),
        }

        if self.daily_target or self.extra_play:
            context["guess_url"] = self._get_guess_url()
            context["background_url"] = self.game.background_image.url if self.game.background_image else None

            if self.daily_target:
                yesterday_target = TargetService(self.game, self.request.user).get_yesterday_target(
                    today_date=self.daily_target.date
                )
                if yesterday_target:
                    context["yesterday_target_name"] = yesterday_target.target.name

        return context

    def _get_guess_url(self):
        """Retrieve the AJAX guess submission URL endpoint."""

        return reverse("ajax_guess", args=[self.game.slug])
