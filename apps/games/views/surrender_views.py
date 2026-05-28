from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.accounts.models import Challenge

from apps.games.views.helpers import process_surrender, resolve_play_context


@require_POST
@login_required
@never_cache
@csrf_protect
def surrender_daily_game(request, slug: str, mode_slug=None):
    game, mode, _, daily_target = resolve_play_context(request, slug, mode_slug)
    if not daily_target:
        return JsonResponse({"error": "No daily target set."}, status=400)
    return process_surrender(request, game=game, daily_target=daily_target)


@require_POST
@login_required
@never_cache
@csrf_protect
def surrender_extra_game(request, extra_id: int):
    from apps.games.models import ExtraDailyPlay

    extra_play = get_object_or_404(ExtraDailyPlay, pk=extra_id, user=request.user)
    return process_surrender(request, game=extra_play.game, extra_play=extra_play)


@require_POST
@login_required
@never_cache
@csrf_protect
def surrender_challenge_game(request, challenge_id: int):
    challenge = get_object_or_404(Challenge, pk=challenge_id)
    if request.user not in (challenge.challenger, challenge.opponent):
        return JsonResponse({"error": "Unauthorized."}, status=403)
    return process_surrender(request, game=challenge.game, challenge=challenge)
