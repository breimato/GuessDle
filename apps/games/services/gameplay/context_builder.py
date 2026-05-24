"""Service to construct the templates rendering context for active play sessions."""

import json
from django.urls import reverse

from apps.games.attempts import build_attempts
from apps.games.models import GameAttempt
from apps.accounts.services.score_service import ScoreService
from .hint_reveal_service import HintRevealService
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
        hint_service = HintRevealService(session, self.game, target_item)
        hint_state = hint_service.get_hint_state()

        context = {
            "game": self.game,
            "target": target_item,
            "attempts": attempts,
            "previous_guesses": [attempt.guess for attempt in attempts_query],
            "won": has_won,
            "can_play": can_play,
            "remaining_names_json": json.dumps(remaining_names),
            "hint_state": hint_state,
            "reveal_hint_url": self._get_reveal_hint_url(),
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

            if self.extra_play:
                score_service = ScoreService(self.request.user, self.game)
                global_average = score_service.calculate_global_average_of_averages(exclude_user=True)
                if global_average is None:
                    global_average = score_service.calculate_user_average_attempts()

                current_attempts = len(attempts)

                bet_won = False
                if has_won:
                    if global_average is not None:
                        bet_won = float(current_attempts) < float(global_average)
                    else:
                        bet_won = True

                bet_amount = self.extra_play.bet_amount
                bonus_points = bet_amount * 1.5 if bet_won else 0
                net_profit = bonus_points - bet_amount if bet_won else 0

                context.update({
                    "extra_play": self.extra_play,
                    "bet_amount": bet_amount,
                    "global_average": global_average,
                    "current_attempts": current_attempts,
                    "bet_won": bet_won,
                    "points_awarded": bonus_points,
                    "net_profit": net_profit,
                    "bet_tracking": {
                        "bet_amount": bet_amount,
                        "global_average": global_average,
                        "current_attempts": current_attempts,
                        "bet_won": bet_won,
                    },
                })

        return context

    def _get_guess_url(self):
        """Retrieve the AJAX guess submission URL endpoint."""

        if self.extra_play:
            return reverse("ajax_guess_extra", args=[self.extra_play.id])
        return reverse("ajax_guess", args=[self.game.slug])

    def _get_reveal_hint_url(self):
        """Retrieve the AJAX column-hint reveal URL endpoint."""

        if self.extra_play:
            return reverse("ajax_reveal_hint_extra", args=[self.extra_play.id])
        if self.challenge:
            return reverse("ajax_reveal_hint_challenge", args=[self.challenge.id])
        return reverse("ajax_reveal_hint", args=[self.game.slug])
