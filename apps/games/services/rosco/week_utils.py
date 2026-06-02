from datetime import date, timedelta

from django.conf import settings
from django.utils import timezone

from apps.games.models import Game, GameMode, WeeklyRosco

ROSCO_PERIOD_DAYS = 7
SATURDAY_WEEKDAY = 5


def rosco_play_weekdays() -> tuple[int, ...]:
    configured = getattr(settings, "ROSCO_PLAY_WEEKDAYS", (SATURDAY_WEEKDAY,))
    return tuple(configured or (SATURDAY_WEEKDAY,))


def is_rosco_play_day(value: date | None = None) -> bool:
    target = value or timezone.localdate()
    return target.weekday() in rosco_play_weekdays()


def current_rosco_saturday(value: date | None = None) -> date:
    target = value or timezone.localdate()
    return target - timedelta(days=(target.weekday() - SATURDAY_WEEKDAY) % 7)


def rosco_anchor_date(game: Game, mode: GameMode, is_team: bool) -> date:
    first = (
        WeeklyRosco.objects.filter(game=game, mode=mode, is_team=is_team)
        .order_by("week_start")
        .values_list("week_start", flat=True)
        .first()
    )
    return current_rosco_saturday(first) if first else current_rosco_saturday()


def current_rosco_period_start(
    game: Game,
    mode: GameMode,
    is_team: bool,
    value: date | None = None,
) -> date:
    target = value or timezone.localdate()
    anchor = rosco_anchor_date(game, mode, is_team)
    if target < anchor:
        return anchor
    elapsed = (current_rosco_saturday(target) - anchor).days
    return anchor + timedelta(days=(elapsed // ROSCO_PERIOD_DAYS) * ROSCO_PERIOD_DAYS)


def rosco_week_number(weekly_rosco: WeeklyRosco) -> int:
    anchor = rosco_anchor_date(
        weekly_rosco.game,
        weekly_rosco.mode,
        weekly_rosco.is_team,
    )
    return ((weekly_rosco.week_start - anchor).days // ROSCO_PERIOD_DAYS) + 1


def week_label(weekly_rosco: WeeklyRosco) -> str:
    return f"Semana {rosco_week_number(weekly_rosco)}"
