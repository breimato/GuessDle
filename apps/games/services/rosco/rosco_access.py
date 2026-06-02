from django.utils import timezone

from apps.games.services.rosco.week_utils import is_rosco_play_day

TEAM_ONLY_MESSAGE = "Pasapalabra solo está disponible para cuentas de equipo."
SATURDAY_ONLY_MESSAGE = "Pasapalabra solo está disponible los sábados."


def is_team_account(user) -> bool:
    return bool(getattr(getattr(user, "profile", None), "is_team_account", False))


def user_can_see_rosco(user) -> bool:
    return is_team_account(user)


def rosco_is_available_today() -> bool:
    return is_rosco_play_day(timezone.localdate())


def user_can_play_rosco(user) -> bool:
    return user_can_see_rosco(user) and rosco_is_available_today()
