import json

from django.http import JsonResponse

from apps.games.services.play_session.play_context import PlayContext

from apps.games.services.play_session.context_builder import ContextBuilder
from apps.games.services.play_session.guess_processor import GuessProcessor

from apps.games.views.helpers import hint_state_from_context


def PlaySessionRef(*, daily_target=None, extra_play=None, challenge=None) -> PlayContext:
    return PlayContext.exactly_one(
        daily_target=daily_target,
        extra_play=extra_play,
        challenge=challenge,
    )


def build_context(request, game, session_ref: PlayContext) -> dict:
    return ContextBuilder(
        request,
        game,
        daily_target=session_ref.daily_target,
        extra_play=session_ref.extra_play,
        challenge=session_ref.challenge,
    ).build()


def reject_if_not_playable(context: dict) -> JsonResponse | None:
    if context["can_play"]:
        return None
    return JsonResponse({"error": "You cannot play anymore."}, status=403)


def build_attempt_payload(context: dict, is_correct: bool, points_data: dict) -> dict:
    last_attempt = context["attempts"][0]
    payload = {
        "won": is_correct,
        "attempt": {
            "name": last_attempt["name"],
            "icon": last_attempt.get("icon"),
            "feedback": last_attempt["feedback"],
            "guess_image_url": last_attempt.get("guess_image_url"),
        },
        "remaining_names": json.loads(context["remaining_names_json"]),
        "hint_state": hint_state_from_context(context),
    }
    payload.update(points_data)
    return payload


def process_guess_request(request, game, session_ref: PlayContext) -> JsonResponse:
    context = build_context(request, game, session_ref)
    blocked = reject_if_not_playable(context)
    if blocked:
        return blocked

    is_valid, is_correct, points_data = GuessProcessor(game, request.user).process(
        request,
        daily_target=session_ref.daily_target,
        extra_play=session_ref.extra_play,
        challenge=session_ref.challenge,
    )
    if not is_valid:
        return JsonResponse({"error": "Invalid attempt."}, status=400)

    context = build_context(request, game, session_ref)
    return JsonResponse(build_attempt_payload(context, is_correct, points_data))
