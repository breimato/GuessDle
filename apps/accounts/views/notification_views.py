from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.accounts.services.dashboard.dashboard_context import active_games_queryset
from apps.accounts.services.dashboard.player_stats_service import PlayerStatsService
from apps.accounts.services.dashboard.ranking_scope import ranking_modes_for_game
from apps.accounts.services.notifications.notification_service import NotificationService
from apps.common.utils import json_success


def _build_stats_sync_payload(user):
    return {
        "games": PlayerStatsService.get_user_games_stats(user),
        "global_elo": PlayerStatsService.get_global_elo(user),
    }


def _build_ranking_sync_payload(user):
    available_games = list(active_games_queryset().prefetch_related("modes"))
    return {
        "global_ranking": PlayerStatsService.build_global_ranking(),
        "ranking_by_game": PlayerStatsService.build_ranking_per_game(),
        "ranking_has_modes": {
            game.slug: bool(ranking_modes_for_game(game))
            for game in available_games
        },
    }


@login_required
@never_cache
def notifications_poll(request):
    NotificationService.migrate_legacy_unread(request.user)
    unread = list(NotificationService.fetch_unread(request.user))
    payload = {
        "notifications": [
            NotificationService.serialize(notification)
            for notification in unread
        ],
    }
    if request.GET.get("include_dashboard") == "1":
        payload["dashboard_sync"] = NotificationService.build_dashboard_sync(
            request.user,
            unread,
            request,
        )
    if request.GET.get("include_stats") == "1":
        payload["stats_sync"] = _build_stats_sync_payload(request.user)
    if request.GET.get("include_rankings") == "1":
        payload["ranking_sync"] = _build_ranking_sync_payload(request.user)
    return json_success(payload)


@require_POST
@login_required
@csrf_protect
def notifications_ack(request):
    raw_ids = request.POST.get("ids", "")
    notification_ids = [
        int(value)
        for value in raw_ids.split(",")
        if value.strip().isdigit()
    ]
    acked_count = NotificationService.ack(request.user, notification_ids)
    return json_success({"acked": acked_count})
