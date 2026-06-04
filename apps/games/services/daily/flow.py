from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse

from apps.accounts.models import Challenge
from apps.accounts.services.notifications.notification_service import NotificationService
from apps.games.models import Game
from apps.accounts.services.challenges.challenge_resolution_service import ChallengeResolutionService
from apps.accounts.services.challenges.challenge_view_helper import ChallengeViewHelper
from apps.games.services.play_session.context_builder import ContextBuilder
from apps.games.services.extra.extra_daily_service import ExtraDailyService
from apps.games.services.play_session.guess_processor import GuessProcessor
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.services.catalog.play_background import resolve_background_url
from apps.games.constants import is_league_game, is_one_piece_game
from apps.games.services.catalog.mode_select_service import ModeSelectService
from apps.games.services.daily.target_service import TargetService

from apps.games.views.guess_responses import build_attempt_payload, reject_if_not_playable
from apps.accounts.services.challenges.challenge_points import challenge_points_delta_for_user


def should_show_mode_select(game: Game, mode_slug) -> bool:
    return ModeResolver(game).has_modes() and not mode_slug


def render_mode_select(request, game: Game, user, slug: str):
    modes = ModeSelectService(game, user).build_entries()

    return render(
        request,
        "games/mode_select.html",
        {
            "game": game,
            "modes": modes,
            "is_league_mode_select": is_league_game(game.slug),
            "is_one_piece_mode_select": is_one_piece_game(game.slug),
        },
    )


def render_missing_daily_target(request, game: Game, mode):
    messages.error(request, "The character for today has not been generated yet.")
    return render(
        request,
        "games/play.html",
        {
            "game": game,
            "game_mode": mode,
            "background_url": resolve_background_url(game, mode),
        },
    )


def handle_daily_post(request, game: Game, daily_target, user, is_ajax: bool):
    context = ContextBuilder(request, game, daily_target=daily_target).build()
    blocked = reject_if_not_playable(context)
    if blocked:
        if is_ajax:
            return blocked
        messages.error(request, "You cannot play anymore.")
        return render(request, "games/play.html", context)

    is_valid, is_correct, points_data = GuessProcessor(game, user).process(
        request, daily_target=daily_target
    )
    if not is_valid:
        if is_ajax:
            return JsonResponse({"error": "Invalid attempt."}, status=400)
        messages.error(request, "Invalid or duplicate attempt.")
        return render(request, "games/play.html", context)

    context = ContextBuilder(request, game, daily_target=daily_target).build()
    if is_correct:
        context["won"] = True
        context["target"] = daily_target
    context.update(points_data)

    if is_ajax:
        return JsonResponse(build_attempt_payload(context, is_correct, points_data))
    return render(request, "games/play.html", context)


def render_daily_play_page(request, game: Game, daily_target, mode, user):
    context = ContextBuilder(request, game, daily_target=daily_target).build()
    extra_daily_service = ExtraDailyService(user, game, mode=mode)
    context.update(
        {
            "slug": game.slug,
            "extra_id": None,
            "max_extras_reached": extra_daily_service.max_reached(),
            "background_url": resolve_background_url(game, mode),
        }
    )
    return render(request, "games/play.html", context)


def ensure_challenge_target(challenge: Challenge, user):
    if challenge.target:
        return challenge

    challenge.target = TargetService(
        challenge.game, user, mode=challenge.mode
    ).get_random_item()
    challenge.save(update_fields=["target"])
    return challenge


def handle_challenge_post(request, challenge: Challenge, challenge_view_helper: ChallengeViewHelper):
    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
    if not challenge_view_helper.assign_attempts_from_post():
        if is_ajax:
            return JsonResponse({"error": "Invalid attempts value."}, status=400)
        return redirect("play_challenge", challenge_id=challenge.id)

    challenge.refresh_from_db()
    if not challenge.completed:
        NotificationService.notify_rival_finished(challenge, request.user)

    resolution_result = ChallengeResolutionService(
        challenge, acting_user=request.user
    ).resolve_and_assign_points()
    challenge.refresh_from_db()

    if not is_ajax:
        return redirect("dashboard")

    points_delta = challenge_points_delta_for_user(challenge, request.user)
    if resolution_result.get("point_deltas"):
        points_delta = resolution_result["point_deltas"].get(request.user.username, points_delta)

    return JsonResponse(
        {
            "completed": challenge.completed,
            "winner": challenge.winner.username if challenge.winner else None,
            "challenger": challenge.challenger.username,
            "opponent": challenge.opponent.username,
            "current_user": request.user.username,
            "challenger_attempts": challenge.challenger_attempts,
            "opponent_attempts": challenge.opponent_attempts,
            "result_status": resolution_result.get("status"),
            "stake_points": float(challenge.stake_points or 0),
            "points_delta": points_delta,
        }
    )


def render_challenge_play_page(request, challenge: Challenge):
    context = ContextBuilder(request, challenge.game, challenge=challenge).build()
    context.update(
        {
            "game": challenge.game,
            "is_challenge": True,
            "challenge_id": challenge.id,
            "background_url": (
                challenge.game.background_image.url
                if challenge.game.background_image
                else None
            ),
            "guess_url": reverse("ajax_guess_challenge", args=[challenge.id]),
            "challenge_report_url": reverse("play_challenge", args=[challenge.id]),
            "is_challenge_js": "true",
        }
    )
    return render(request, "games/play.html", context)
