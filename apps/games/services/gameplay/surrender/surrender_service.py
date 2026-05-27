from apps.games.services.gameplay.play_session_service import PlaySessionService

from .challenge_surrender_handler import ChallengeSurrenderHandler
from .extra_play_surrender_handler import ExtraPlaySurrenderHandler
from .play_context import SurrenderPlayContext
from .session_eligibility_checker import SurrenderSessionEligibilityChecker
from .surrender_result import SurrenderResult


class SurrenderService:
    def __init__(self, game, user):
        self.game = game
        self.user = user

    def process(self, *, daily_target=None, extra_play=None, challenge=None):
        play_context = SurrenderPlayContext.exactly_one(
            daily_target=daily_target,
            extra_play=extra_play,
            challenge=challenge,
        )
        play_session = self._load_play_session(play_context)
        SurrenderSessionEligibilityChecker.ensure_eligible(play_session)
        self._mark_as_surrendered(play_session)

        points_data = {}
        challenge_data = None

        if play_context.extra_play:
            points_data = ExtraPlaySurrenderHandler(self.user, self.game).apply(
                play_session,
                play_context.extra_play,
            )

        if play_context.challenge:
            challenge_data = ChallengeSurrenderHandler(self.user).apply(
                play_session,
                play_context.challenge,
            )

        return SurrenderResult(
            target_name=play_context.target_item.name,
            points_data=points_data,
            challenge_data=challenge_data,
        )

    def _load_play_session(self, play_context):
        return PlaySessionService.get_or_create(
            self.user,
            self.game,
            **play_context.session_lookup_kwargs(),
        )

    def _mark_as_surrendered(self, play_session):
        play_session.surrendered = True
        play_session.save(update_fields=["surrendered"])
