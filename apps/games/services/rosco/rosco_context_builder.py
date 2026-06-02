from django.urls import reverse

from apps.games.models import RoscoJackpotWinner, RoscoSessionStatus
from apps.games.services.catalog.play_background import resolve_background_url
from apps.games.services.rosco.rosco_session_state import session_is_playable
from apps.games.services.rosco.rosco_turn_processor import RoscoTurnProcessor
from apps.games.services.rosco.week_utils import rosco_week_number, week_label
from apps.games.services.rosco.weekly_pot_service import WeeklyPotService
from apps.games.services.rosco.weekly_rosco_service import WeeklyRoscoService


class RoscoContextBuilder:
    def __init__(self, request, game, mode):
        self.request = request
        self.game = game
        self.mode = mode
        self.user = request.user
        self.service = WeeklyRoscoService(game, mode, self.user)

    def build(self) -> dict:
        if not WeeklyRoscoService.has_question_bank(self.game):
            return {"rosco_unavailable": True, "game": self.game, "game_mode": self.mode}

        weekly_rosco = self.service.ensure_current_weekly_rosco()
        session = self.service.get_or_create_session(weekly_rosco)
        entry = self.service.get_entry_for_letter(weekly_rosco, session.rosco_current_letter)
        processor = RoscoTurnProcessor(session, weekly_rosco, entry)
        state = processor._build_response()

        slug = self.game.slug
        mode_slug = self.mode.slug
        pot = WeeklyPotService(weekly_rosco).get_pot()
        winner = RoscoJackpotWinner.objects.filter(
            weekly_rosco=weekly_rosco,
            user=self.user,
        ).first()

        return {
            "game": self.game,
            "game_mode": self.mode,
            "weekly_rosco": weekly_rosco,
            "week_label": week_label(weekly_rosco),
            "week_number": rosco_week_number(weekly_rosco),
            "session": session,
            "rosco_state": state,
            "pot_amount": pot.pot_amount,
            "background_url": resolve_background_url(self.game, self.mode),
            "back_to_modes_url": reverse("play", args=[slug]),
            "answer_url": reverse("rosco_answer", args=[slug, mode_slug]),
            "pass_url": reverse("rosco_pass", args=[slug, mode_slug]),
            "surrender_url": reverse("rosco_surrender", args=[slug, mode_slug]),
            "can_play": session_is_playable(session),
            "session_status": session.rosco_status or RoscoSessionStatus.IN_PROGRESS,
            "is_perfect_winner": bool(winner),
            "share_amount": winner.share_amount if winner else 0,
        }
