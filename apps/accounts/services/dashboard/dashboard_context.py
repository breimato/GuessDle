from django.contrib.auth.models import User
from django.db import models
from django.utils.timezone import now

from apps.accounts.models import Challenge
from apps.accounts.services.challenges.challenge_scope import (
    challenge_modes_for_game,
    is_challengeable_game,
    requires_challenge_mode_selection,
)
from apps.accounts.services.dashboard.extra_play_index import (
    build_extra_play_index,
    resolve_game_redirect_url,
)
from apps.accounts.services.dashboard.player_stats_service import PlayerStatsService
from apps.accounts.services.dashboard.ranking_scope import ranking_modes_for_game
from apps.games.models import ExtraDailyPlay, Game
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.services.daily.target_service import TargetService


def active_games_queryset():
    return Game.objects.filter(active=True).order_by("name")


def enrich_available_games(request, available_games):
    today_extras = ExtraDailyPlay.objects.filter(
        user=request.user,
        created_at__date=now().date(),
    ).select_related("game", "mode")
    extra_index = build_extra_play_index(today_extras)

    for game in available_games:
        resolver = ModeResolver(game)
        service = TargetService(game, request.user)

        game.redirect_url = resolve_game_redirect_url(game, extra_index, request.user)
        game.has_pending_daily = service.has_any_unresolved_mode()
        game.active_modes = list(resolver.active_modes()) if resolver.has_modes() else []
        game.ranking_modes = ranking_modes_for_game(game)
        game.active_extra_by_mode = {
            mode.slug: extra_index.active_by_game_mode.get((game.slug, mode.slug))
            for mode in game.active_modes
        }

    return available_games


def build_challengeable_games(available_games):
    challengeable_games = []
    for game in available_games:
        if not is_challengeable_game(game):
            continue
        game.challenge_modes = challenge_modes_for_game(game)
        game.requires_challenge_mode = requires_challenge_mode_selection(game)
        challengeable_games.append(game)
    return challengeable_games


def build_dashboard_context(request):
    user = request.user
    available_games = list(active_games_queryset().prefetch_related("modes"))
    enrich_available_games(request, available_games)
    challengeable_games = build_challengeable_games(available_games)

    return {
        "available_games": available_games,
        "challengeable_games": challengeable_games,
        "user_stats": {
            "games": PlayerStatsService.get_user_games_stats(user),
            "global_elo": PlayerStatsService.get_global_elo(user),
        },
        "global_ranking": PlayerStatsService.build_global_ranking(),
        "ranking_by_game": PlayerStatsService.build_ranking_per_game(),
        "ranking_has_modes": {
            game.slug: bool(game.ranking_modes)
            for game in available_games
        },
        "pending_challenges": Challenge.objects.filter(opponent=user, accepted=False),
        "active_challenges": Challenge.objects.filter(
            accepted=True,
            completed=False,
        ).filter(models.Q(challenger=user) | models.Q(opponent=user)),
        "active_challenges_to_play": Challenge.objects.filter(
            accepted=True,
            completed=False,
            challenger=user,
        ),
        "sent_pending_challenges": Challenge.objects.filter(
            challenger=user,
            accepted=False,
            completed=False,
        ),
        "users": User.objects.exclude(id=user.id),
    }
