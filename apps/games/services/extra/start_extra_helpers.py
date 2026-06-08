from django.utils import timezone

from apps.games.models import DailyTarget, ExtraDailyPlay, Game, GameAttempt, PlaySessionType
from apps.games.services.catalog.mode_resolver import ModeResolver


def _resolved_daily_mode_today(game: Game, user):
    today = timezone.localdate()
    daily_target_ids = DailyTarget.objects.filter(
        game=game,
        date=today,
        mode__isnull=False,
    ).values_list("id", flat=True)
    if not daily_target_ids:
        return None

    winning_attempt = (
        GameAttempt.objects.filter(
            user=user,
            game=game,
            is_correct=True,
            session__session_type=PlaySessionType.DAILY,
            session__reference_id__in=daily_target_ids,
        )
        .select_related("session__mode")
        .order_by("-attempted_at")
        .first()
    )
    if winning_attempt and winning_attempt.session.mode_id:
        return winning_attempt.session.mode
    return None


def resolve_extra_mode(game: Game, user, mode_slug: str | None):
    resolver = ModeResolver(game)
    mode = resolver.resolve(mode_slug) if mode_slug else None
    if mode or not resolver.has_modes():
        return mode

    today = timezone.localdate()
    latest_extra = (
        ExtraDailyPlay.objects.filter(
            user=user,
            game=game,
            created_at__date=today,
        )
        .select_related("mode")
        .order_by("-created_at")
        .first()
    )
    if latest_extra and latest_extra.mode_id:
        return latest_extra.mode
    return _resolved_daily_mode_today(game, user)
