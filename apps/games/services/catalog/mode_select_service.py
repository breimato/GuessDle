from django.urls import reverse
from django.utils.timezone import localtime

from apps.games.models import ExtraDailyPlay, Game, GameMode, RoscoSessionStatus
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.services.daily.target_service import TargetService
from apps.games.services.emoji.daily_target_service import EmojiDailyTargetService
from apps.games.services.extra.extra_daily_service import ExtraDailyService
from apps.games.services.proximity.status_service import ProximityStatusService
from apps.games.services.rosco.rosco_access import rosco_is_available_today, user_can_see_rosco
from apps.games.services.rosco.week_utils import week_label
from apps.games.services.rosco.weekly_pot_service import WeeklyPotService
from apps.games.services.rosco.weekly_rosco_service import WeeklyRoscoService


def rosco_status_label(status: str) -> str:
    labels = {
        RoscoSessionStatus.IN_PROGRESS: "En curso",
        RoscoSessionStatus.FAILED: "Fallaste esta semana",
        RoscoSessionStatus.COMPLETED: "Completado esta semana",
        RoscoSessionStatus.WON_PERFECT: "¡Rosco completo!",
        RoscoSessionStatus.SURRENDERED: "Rendida",
    }
    return labels.get(status, "En curso")


class ModeSelectService:
    def __init__(self, game: Game, user):
        self.game = game
        self.user = user
        self.slug = game.slug

    def build_entries(self) -> list[dict]:
        entries = []
        for mode in ModeResolver(self.game).active_modes():
            entry = self._entry_for_mode(mode)
            if entry is not None:
                entries.append(entry)
        return entries

    def next_playable_entry(self, current_mode: GameMode | None) -> dict | None:
        playable = [entry for entry in self.build_entries() if self._is_playable(entry)]
        if len(playable) <= 1 or not current_mode:
            return None

        slugs = [entry["mode"].slug for entry in playable]
        if current_mode.slug not in slugs:
            return playable[0]

        next_index = slugs.index(current_mode.slug) + 1
        if next_index >= len(playable):
            return None
        return playable[next_index]

    @staticmethod
    def _is_playable(entry: dict) -> bool:
        return not (
            entry.get("rosco_unavailable")
            or entry.get("emoji_unavailable")
            or entry.get("proximity_unavailable")
        )

    def _entry_for_mode(self, mode: GameMode) -> dict | None:
        if mode.is_rosco:
            if not user_can_see_rosco(self.user) or not rosco_is_available_today():
                return None

            if not WeeklyRoscoService.has_question_bank(self.game):
                return {
                    "mode": mode,
                    "is_rosco": True,
                    "rosco_unavailable": True,
                    "play_url": reverse("play_mode", args=[self.slug, mode.slug]),
                    "pot_amount": 0,
                    "rosco_status_label": "No disponible",
                }

            rosco_service = WeeklyRoscoService(self.game, mode, self.user)
            weekly_rosco = rosco_service.ensure_current_weekly_rosco()
            session = rosco_service.get_or_create_session(weekly_rosco)
            pot = WeeklyPotService(weekly_rosco).get_pot()
            status = session.rosco_status or RoscoSessionStatus.IN_PROGRESS
            return {
                "mode": mode,
                "is_rosco": True,
                "play_url": reverse("play_mode", args=[self.slug, mode.slug]),
                "pot_amount": pot.pot_amount,
                "week_label": week_label(weekly_rosco),
                "rosco_status": status,
                "rosco_status_label": rosco_status_label(status),
            }

        if mode.is_proximity:
            status = ProximityStatusService(self.game, self.user, mode)
            if not status.pool_available():
                return {
                    "mode": mode,
                    "is_rosco": False,
                    "is_proximity": True,
                    "proximity_unavailable": True,
                    "resolved": False,
                    "play_url": reverse("play_mode", args=[self.slug, mode.slug]),
                    "proximity_status_label": "No disponible",
                }
            return {
                "mode": mode,
                "is_rosco": False,
                "is_proximity": True,
                "proximity_unavailable": False,
                "resolved": status.is_resolved_today(),
                "play_url": reverse("play_mode", args=[self.slug, mode.slug]),
            }

        if mode.is_emoji:
            service = TargetService(self.game, self.user, mode=mode)
            if not EmojiDailyTargetService.has_clue_bank(self.game):
                return {
                    "mode": mode,
                    "is_rosco": False,
                    "is_emoji": True,
                    "emoji_unavailable": True,
                    "resolved": False,
                    "play_url": reverse("play_mode", args=[self.slug, mode.slug]),
                    "emoji_status_label": "No disponible",
                }
            return {
                "mode": mode,
                "is_rosco": False,
                "is_emoji": True,
                "emoji_unavailable": False,
                "resolved": service.is_daily_resolved(),
                "play_url": reverse("play_mode", args=[self.slug, mode.slug]),
            }

        service = TargetService(self.game, self.user, mode=mode)
        extra_service = ExtraDailyService(self.user, self.game, mode=mode)
        active_extra = ExtraDailyPlay.objects.filter(
            user=self.user,
            game=self.game,
            mode=mode,
            created_at__date=localtime().date(),
            completed=False,
        ).first()
        return {
            "mode": mode,
            "is_rosco": False,
            "resolved": service.is_daily_resolved(),
            "play_url": reverse("play_mode", args=[self.slug, mode.slug]),
            "active_extra_id": active_extra.id if active_extra else None,
            "can_start_extra": service.is_daily_resolved()
            and not extra_service.max_reached()
            and not active_extra,
            "max_extras_reached": extra_service.max_reached(),
        }
