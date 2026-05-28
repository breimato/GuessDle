from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.accounts.services.challenges.challenge_resolution_service import (
    ChallengeResolutionService,
)
from apps.accounts.services.challenges.challenge_view_helper import ChallengeViewHelper
from apps.accounts.models import Challenge
from apps.common.utils import json_error, json_success


@login_required
@csrf_protect
def create_challenge(request):
    challenge, error_message = ChallengeViewHelper.create_challenge(request)
    if error_message:
        return json_error(error_message)

    card_html = render_to_string(
        "partials/sent_challenge_card.html",
        {"challenge": challenge},
        request=request,
    )
    return json_success({"card": card_html})


@require_POST
@login_required
def cancel_challenge(request, challenge_id):
    is_cancelled = ChallengeViewHelper.cancel_challenge(request, challenge_id)
    if not is_cancelled:
        return json_error("Could not cancel challenge")
    return json_success({"id": challenge_id})


@require_POST
@login_required
def reject_challenge(request, challenge_id):
    is_rejected = ChallengeViewHelper.reject_challenge(request, challenge_id)
    if not is_rejected:
        return json_error("Could not reject challenge")
    return json_success({"id": challenge_id})


@require_POST
@login_required
def accept_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, pk=challenge_id, accepted=False, completed=False)
    challenge_view_helper = ChallengeViewHelper(request, challenge)
    accepted, acceptance_error = challenge_view_helper.accept_if_needed()
    if not accepted:
        return json_error(
            acceptance_error
            or "No puedes aceptar este reto porque todavía no es seguro que tengas esos puntos."
        )
    return json_success(
        {
            "id": challenge_id,
            "play_url": reverse("play_challenge", args=[challenge_id]),
        }
    )


@login_required
@csrf_protect
def complete_challenge(request, challenge_id):
    challenge = get_object_or_404(Challenge, pk=challenge_id, accepted=True, completed=False)
    result = ChallengeResolutionService(challenge, acting_user=request.user).resolve_and_assign_points()

    if result["status"] == "already-resolved":
        return JsonResponse({"status": "already-resolved"})
    if result["status"] == "tie":
        return JsonResponse({
            "status": "tie",
            "users": [user.username for user in result["users"]],
        })
    if result["status"] == "winner":
        return JsonResponse({
            "status": "success",
            "winner": result["winner"].username,
            "loser": result["loser"].username,
        })
    return JsonResponse({"status": "error"})
