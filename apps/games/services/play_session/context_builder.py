import json

from django.urls import reverse

from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.accounts.services.wallet.score_service import ScoreService
from apps.games.services.extra.payout import (
    compute_extra_bet_payout,
    evaluate_extra_bet_won,
)
from apps.games.services.extra.session import resolve_global_average
from apps.games.services.hints.hint_reveal_service import HintRevealService
from apps.games.services.catalog.item_pool_service import ItemPoolService
from apps.games.services.catalog.play_background import resolve_background_url
from apps.games.services.catalog.play_mode_navigation import next_mode_navigation
from apps.games.services.play_session.play_context import PlayContext
from apps.games.services.play_session.play_url_registry import PlayUrlRegistry
from apps.games.services.play_session.session_context_loader import SessionContextLoader
from apps.games.services.daily.target_service import TargetService


class ContextBuilder:

    def __init__(self, request, game, daily_target=None, challenge=None, extra_play=None):
        if daily_target is None and challenge is None and extra_play is None:
            raise ValueError("Must specify daily_target, challenge, or extra_play.")

        self.request = request
        self.game = game
        self.daily_target = daily_target
        self.challenge = challenge
        self.extra_play = extra_play

    def build(self):
        mode = self._active_mode()
        session, target_item, attempts_query, attempts = SessionContextLoader(
            self.request,
            self.game,
            daily_target=self.daily_target,
            extra_play=self.extra_play,
            challenge=self.challenge,
        ).load()

        has_won = attempts_query.filter(is_correct=True).exists()
        can_play = not has_won and not session.surrendered

        guessed_item_ids = [attempt.guess_id for attempt in attempts_query]
        remaining_names = list(
            ItemPoolService(self.game, mode)
            .get_queryset()
            .exclude(id__in=guessed_item_ids)
            .values_list("name", flat=True)
        )

        hint_state = HintRevealService(session, self.game, target_item).get_hint_state()
        url_registry = PlayUrlRegistry(
            self.game,
            daily_target=self.daily_target,
            extra_play=self.extra_play,
            challenge=self.challenge,
        )

        context = {
            "game": self.game,
            "target": target_item,
            "attempts": attempts,
            "previous_guesses": [attempt.guess for attempt in attempts_query],
            "won": has_won,
            "surrendered": session.surrendered,
            "can_play": can_play,
            "remaining_names_json": json.dumps(remaining_names),
            "hint_state": hint_state,
            "reveal_hint_url": url_registry.reveal_hint_url(),
            "game_mode": mode,
            "surrender_url": url_registry.surrender_url(),
        }

        if mode and ModeResolver(self.game).has_modes() and not self.challenge:
            context["back_to_modes_url"] = reverse("play", args=[self.game.slug])
            context.update(next_mode_navigation(self.game, self.request.user, mode))

        if self.daily_target or self.extra_play:
            context["guess_url"] = url_registry.guess_url()
            context["background_url"] = resolve_background_url(self.game, mode)
            self._apply_daily_extensions(context, mode)

            if self.extra_play:
                context.update(self._build_extra_play_context(attempts, has_won))

        return context

    def _apply_daily_extensions(self, context, mode):
        if not self.daily_target:
            return

        yesterday_target = TargetService(
            self.game, self.request.user, mode=mode
        ).get_yesterday_target(today_date=self.daily_target.date)
        if yesterday_target:
            context["yesterday_target_name"] = yesterday_target.target.name

    def _build_extra_play_context(self, attempts, has_won):
        score_service = ScoreService(
            self.request.user, self.game, mode=self.extra_play.mode
        )
        global_average = resolve_global_average(score_service)
        current_attempts = len(attempts)
        bet_won = has_won and evaluate_extra_bet_won(current_attempts, score_service)
        bet_amount = self.extra_play.bet_amount
        payout = compute_extra_bet_payout(bet_amount, bet_won)

        return {
            "extra_play": self.extra_play,
            "bet_amount": bet_amount,
            "global_average": global_average,
            "current_attempts": current_attempts,
            "bet_won": bet_won,
            "points_awarded": payout.points_awarded,
            "net_profit": payout.net_profit,
            "bet_tracking": {
                "bet_amount": bet_amount,
                "global_average": global_average,
                "current_attempts": current_attempts,
                "bet_won": bet_won,
            },
        }

    def _active_mode(self):
        return PlayContext.exactly_one(
            daily_target=self.daily_target,
            extra_play=self.extra_play,
            challenge=self.challenge,
        ).mode
