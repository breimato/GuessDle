import json
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.timezone import localtime
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.accounts.models import Challenge
from apps.games.models import ExtraDailyPlay, Game
from apps.games.services.gameplay.challenge_resolution_service import ChallengeResolutionService
from apps.games.services.gameplay.challenge_view_helper import ChallengeViewHelper
from apps.games.services.gameplay.context_builder import ContextBuilder
from apps.games.services.gameplay.extra_daily_service import ExtraDailyService
from apps.games.services.gameplay.guess_processor import GuessProcessor
from apps.games.services.gameplay.hint_reveal_service import HintRevealService
from apps.games.services.gameplay.play_session_service import PlaySessionService
from apps.games.services.gameplay.target_service import TargetService
from apps.games.services.mode_resolver import ModeResolver


def _hint_state_from_context(context):
    return context.get("hint_state", {})


def _resolve_play_context(request, slug, mode_slug=None):
    game = get_object_or_404(Game, slug=slug)
    resolver = ModeResolver(game)
    if resolver.has_modes() and not mode_slug:
        return game, None, resolver, None
    mode = resolver.resolve(mode_slug) if mode_slug else None
    target_service = TargetService(game, request.user, mode=mode)
    daily_target = target_service.get_target_for_today()
    return game, mode, resolver, daily_target


def _process_reveal_hint(request, *, game, target, daily_target=None, extra_play=None, challenge=None):
    attribute = request.POST.get("attribute", "").strip()
    if not attribute:
        return JsonResponse({"error": "Debes elegir una columna."}, status=400)

    session = PlaySessionService.get_or_create(
        request.user,
        game,
        daily_target=daily_target,
        extra_play=extra_play,
        challenge=challenge,
    )
    hint_service = HintRevealService(session, game, target)
    try:
        hint_state = hint_service.reveal(attribute)
    except ValueError as error:
        return JsonResponse({"error": str(error)}, status=400)

    return JsonResponse({"hint_state": hint_state})


@require_POST
@login_required
@never_cache
@csrf_protect
def process_daily_guess(request, slug: str, mode_slug=None):
    game, mode, _, daily_target = _resolve_play_context(request, slug, mode_slug)
    if not daily_target:
        return JsonResponse({"error": "No daily target set."}, status=400)

    context = ContextBuilder(request, game, daily_target=daily_target).build()
    if not context["can_play"]:
        return JsonResponse({"error": "You cannot play anymore."}, status=403)

    is_valid, is_correct, points_data = GuessProcessor(game, request.user).process(
        request, daily_target=daily_target
    )
    if not is_valid:
        return JsonResponse({"error": "Invalid attempt."}, status=400)

    context = ContextBuilder(request, game, daily_target=daily_target).build()
    last_attempt = context["attempts"][0]

    response_data = {
        "won": is_correct,
        "attempt": {
            "name": last_attempt["name"],
            "icon": last_attempt.get("icon"),
            "feedback": last_attempt["feedback"],
            "guess_image_url": last_attempt.get("guess_image_url"),
        },
        "remaining_names": json.loads(context["remaining_names_json"]),
        "hint_state": _hint_state_from_context(context),
    }
    response_data.update(points_data)
    return JsonResponse(response_data)


@require_POST
@login_required
@never_cache
@csrf_protect
def reveal_daily_hint(request, slug: str, mode_slug=None):
    game, mode, _, daily_target = _resolve_play_context(request, slug, mode_slug)
    if not daily_target:
        return JsonResponse({"error": "No daily target set."}, status=400)

    context = ContextBuilder(request, game, daily_target=daily_target).build()
    if not context["can_play"]:
        return JsonResponse({"error": "You cannot play anymore."}, status=403)

    return _process_reveal_hint(
        request,
        game=game,
        target=daily_target.target,
        daily_target=daily_target,
    )


@never_cache
@login_required
@csrf_protect
def play_daily_game(request, slug: str, mode_slug=None):
    game = get_object_or_404(Game, slug=slug)
    resolver = ModeResolver(game)
    user = request.user

    if resolver.has_modes() and not mode_slug:
        modes = []
        for mode in resolver.active_modes():
            service = TargetService(game, user, mode=mode)
            modes.append(
                {
                    "mode": mode,
                    "resolved": service.is_daily_resolved(),
                    "play_url": reverse("play_mode", args=[slug, mode.slug]),
                }
            )
        return render(request, "games/mode_select.html", {"game": game, "modes": modes})

    game, mode, resolver, daily_target = _resolve_play_context(request, slug, mode_slug)

    if not daily_target:
        messages.error(request, "The character for today has not been generated yet.")
        return render(
            request,
            "games/play.html",
            {"game": game, "game_mode": mode},
        )

    is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"

    if request.method == "POST":
        context = ContextBuilder(request, game, daily_target=daily_target).build()
        if not context["can_play"]:
            if is_ajax:
                return JsonResponse({"error": "You cannot play anymore."}, status=403)
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
        last_attempt = context["attempts"][0]
        if is_correct:
            context["won"] = True
            context["target"] = daily_target

        context.update(points_data)

        if is_ajax:
            response_data = {
                "won": is_correct,
                "attempt": {
                    "name": last_attempt["name"],
                    "icon": last_attempt.get("icon"),
                    "feedback": last_attempt["feedback"],
                    "guess_image_url": last_attempt.get("guess_image_url"),
                },
                "remaining_names": json.loads(context["remaining_names_json"]),
                "hint_state": _hint_state_from_context(context),
            }
            response_data.update(points_data)
            return JsonResponse(response_data)
        return render(request, "games/play.html", context)

    context = ContextBuilder(request, game, daily_target=daily_target).build()
    extra_daily_service = ExtraDailyService(user, game, mode=mode)
    context.update(
        {
            "slug": game.slug,
            "extra_id": None,
            "max_extras_reached": extra_daily_service.max_reached(),
        }
    )
    return render(request, "games/play.html", context)


@never_cache
@login_required
@csrf_protect
def play_challenge_game(request, challenge_id: int):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    challenge_view_helper = ChallengeViewHelper(request, challenge)

    challenge_view_helper.accept_if_needed()
    if not challenge_view_helper.ensure_participant():
        return redirect("dashboard")

    if not challenge.target:
        challenge.target = TargetService(
            challenge.game, request.user, mode=challenge.mode
        ).get_random_item()
        challenge.save(update_fields=["target"])

    if request.method == "POST":
        is_ajax = request.headers.get("x-requested-with") == "XMLHttpRequest"
        if not challenge_view_helper.assign_attempts_from_post():
            if is_ajax:
                return JsonResponse({"error": "Invalid attempts value."}, status=400)
            return redirect("play_challenge", challenge_id=challenge.id)

        resolution_result = ChallengeResolutionService(
            challenge, acting_user=request.user
        ).resolve_and_assign_points()

        if is_ajax:
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
                }
            )
        return redirect("dashboard")

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


@require_POST
@login_required
@never_cache
@csrf_protect
def process_challenge_guess(request, challenge_id: int):
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    if request.user not in (challenge.challenger, challenge.opponent):
        return JsonResponse({"error": "Unauthorized."}, status=403)

    game = challenge.game
    context = ContextBuilder(request, game, challenge=challenge).build()
    if not context["can_play"]:
        return JsonResponse({"error": "You cannot play anymore."}, status=403)

    is_valid, is_correct, points_data = GuessProcessor(game, request.user).process(
        request, challenge=challenge
    )
    if not is_valid:
        return JsonResponse({"error": "Invalid attempt."}, status=400)

    context = ContextBuilder(request, game, challenge=challenge).build()
    last_attempt = context["attempts"][0]

    response_data = {
        "won": is_correct,
        "attempt": {
            "name": last_attempt["name"],
            "icon": last_attempt.get("icon"),
            "feedback": last_attempt["feedback"],
            "guess_image_url": last_attempt.get("guess_image_url"),
        },
        "remaining_names": json.loads(context["remaining_names_json"]),
        "hint_state": _hint_state_from_context(context),
    }
    response_data.update(points_data)
    return JsonResponse(response_data)


@require_POST
@login_required
@never_cache
@csrf_protect
def reveal_challenge_hint(request, challenge_id: int):
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    if request.user not in (challenge.challenger, challenge.opponent):
        return JsonResponse({"error": "Unauthorized."}, status=403)

    if not challenge.target:
        return JsonResponse({"error": "Challenge has no target."}, status=400)

    game = challenge.game
    context = ContextBuilder(request, game, challenge=challenge).build()
    if not context["can_play"]:
        return JsonResponse({"error": "You cannot play anymore."}, status=403)

    return _process_reveal_hint(
        request,
        game=game,
        target=challenge.target,
        challenge=challenge,
    )


@login_required
@csrf_protect
def start_extra_daily_game(request, slug: str, mode_slug=None):
    game = get_object_or_404(Game, slug=slug)
    resolver = ModeResolver(game)
    mode = resolver.resolve(mode_slug) if mode_slug else None
    if resolver.has_modes() and not mode:
        return redirect("play", slug=slug)

    user = request.user
    extra_daily_service = ExtraDailyService(user, game, mode=mode)

    if extra_daily_service.max_reached():
        messages.error(
            request,
            "You have already played the maximum of 2 extra games today for this game.",
        )
        return redirect("dashboard")

    target_service = TargetService(game, user, mode=mode)
    if not target_service.is_daily_resolved():
        messages.error(
            request,
            "Debes completar la partida diaria antes de apostar una partida extra.",
        )
        if mode:
            return redirect("play_mode", slug=slug, mode_slug=mode.slug)
        return redirect("play", slug=slug)

    try:
        bet = float(request.POST.get("bet", "0"))
    except ValueError:
        bet = 0

    try:
        extra_play = extra_daily_service.start_extra_play(bet)
    except ValueError as error:
        messages.error(request, str(error))
        return redirect("dashboard")

    return redirect("play_extra_daily", extra_id=extra_play.id)


@login_required
@csrf_protect
def play_extra_daily_game(request, extra_id: int):
    extra_play = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    game = extra_play.game
    extra_daily_service = ExtraDailyService(request.user, game, mode=extra_play.mode)

    if localtime(extra_play.created_at).date() != date.today():
        return redirect("dashboard")

    points_data = {}
    if request.method == "POST":
        if extra_play.completed:
            return redirect("play_extra_daily", extra_id=extra_play.id)
        _, _, points_data = GuessProcessor(game, request.user).process(
            request, extra_play=extra_play
        )

    context = ContextBuilder(request, game, extra_play=extra_play).build()
    context.update(
        {
            "target": extra_play.target,
            "guess_url": reverse("ajax_guess_extra", args=[extra_play.id]),
            "slug": game.slug,
            "extra_id": extra_play.id,
            "max_extras_reached": extra_daily_service.max_reached(),
        }
    )
    if points_data:
        context.update(points_data)
    return render(request, "games/play.html", context)


@require_POST
@login_required
@never_cache
@csrf_protect
def process_extra_guess(request, extra_id: int):
    extra_play = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    game = extra_play.game

    context = ContextBuilder(request, game, extra_play=extra_play).build()
    if not context["can_play"]:
        return JsonResponse({"error": "You cannot play anymore."}, status=403)

    is_valid, is_correct, points_data = GuessProcessor(game, request.user).process(
        request, extra_play=extra_play
    )
    if not is_valid:
        return JsonResponse({"error": "Invalid attempt."}, status=400)

    context = ContextBuilder(request, game, extra_play=extra_play).build()
    last_attempt = context["attempts"][0]

    response_data = {
        "won": is_correct,
        "attempt": {
            "name": last_attempt["name"],
            "icon": last_attempt.get("icon"),
            "feedback": last_attempt["feedback"],
            "guess_image_url": last_attempt.get("guess_image_url"),
        },
        "remaining_names": json.loads(context["remaining_names_json"]),
        "hint_state": _hint_state_from_context(context),
    }
    response_data.update(points_data)
    return JsonResponse(response_data)


@require_POST
@login_required
@never_cache
@csrf_protect
def reveal_extra_hint(request, extra_id: int):
    extra_play = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    game = extra_play.game

    context = ContextBuilder(request, game, extra_play=extra_play).build()
    if not context["can_play"]:
        return JsonResponse({"error": "You cannot play anymore."}, status=403)

    return _process_reveal_hint(
        request,
        game=game,
        target=extra_play.target,
        extra_play=extra_play,
    )
