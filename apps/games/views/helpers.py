from django.http import JsonResponse

from apps.games.services.hints.hint_reveal_service import HintRevealService
from apps.games.services.play_session.play_session_service import PlaySessionService
from apps.games.services.surrender.surrender_request_processor import SurrenderRequestProcessor
from apps.games.services.daily.target_service import TargetService
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.models import Game
from django.shortcuts import get_object_or_404


def hint_state_from_context(context):
    return context.get("hint_state", {})


def resolve_play_context(request, slug, mode_slug=None):
    game = get_object_or_404(Game, slug=slug)
    resolver = ModeResolver(game)
    if resolver.has_modes() and not mode_slug:
        return game, None, resolver, None
    mode = resolver.resolve(mode_slug) if mode_slug else None
    target_service = TargetService(game, request.user, mode=mode)
    daily_target = target_service.get_target_for_today()
    return game, mode, resolver, daily_target


def process_reveal_hint(request, *, game, target, daily_target=None, extra_play=None, challenge=None):
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


def process_surrender(request, *, game, daily_target=None, extra_play=None, challenge=None):
    return SurrenderRequestProcessor(request, game).process(
        daily_target=daily_target,
        extra_play=extra_play,
        challenge=challenge,
    )
