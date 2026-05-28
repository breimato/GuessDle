from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.accounts.models import Challenge
from apps.accounts.services.challenges.challenge_view_helper import ChallengeViewHelper
from apps.games.services.play_session.context_builder import ContextBuilder
from apps.games.views.guess_responses import PlaySessionRef, process_guess_request
from apps.games.services.daily.flow import (
    ensure_challenge_target,
    handle_challenge_post,
    render_challenge_play_page,
)

from apps.games.views.helpers import process_reveal_hint


@never_cache
@login_required
@csrf_protect
def play_challenge_game(request, challenge_id: int):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    challenge_view_helper = ChallengeViewHelper(request, challenge)

    accepted, acceptance_error = challenge_view_helper.accept_if_needed()
    if not accepted:
        messages.error(request, acceptance_error or "No se pudo aceptar el reto.")
        return redirect("dashboard")

    challenge = challenge_view_helper.challenge
    if not challenge_view_helper.ensure_participant():
        return redirect("dashboard")

    challenge = ensure_challenge_target(challenge, request.user)

    if request.method == "POST":
        return handle_challenge_post(request, challenge, challenge_view_helper)

    return render_challenge_play_page(request, challenge)


@require_POST
@login_required
@never_cache
@csrf_protect
def process_challenge_guess(request, challenge_id: int):
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    if request.user not in (challenge.challenger, challenge.opponent):
        return JsonResponse({"error": "Unauthorized."}, status=403)

    return process_guess_request(
        request,
        challenge.game,
        PlaySessionRef(challenge=challenge),
    )


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

    return process_reveal_hint(
        request,
        game=game,
        target=challenge.target,
        challenge=challenge,
    )
