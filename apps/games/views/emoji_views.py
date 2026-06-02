from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST

from apps.games.models import Game
from apps.games.services.catalog.mode_resolver import ModeResolver
from apps.games.services.emoji.context_builder import EmojiContextBuilder
from apps.games.services.emoji.daily_target_service import EmojiDailyTargetService
from apps.games.services.emoji.guess_processor import EmojiGuessProcessor
from apps.games.views.helpers import resolve_play_context


def _resolve_emoji_mode(game: Game, mode_slug: str):
    mode = ModeResolver(game).resolve(mode_slug)
    if not mode.is_emoji:
        raise Http404("Este modo no es de tipo emoji.")
    return mode


def _render_unavailable(request, game: Game, mode, message: str):
    return render(
        request,
        "games/emoji_unavailable.html",
        {
            "game": game,
            "game_mode": mode,
            "message": message,
            "back_to_modes_url": reverse("play", args=[game.slug]),
        },
    )


@never_cache
@login_required
@csrf_protect
def play_emoji_game(request, slug: str, mode_slug: str):
    game = get_object_or_404(Game, slug=slug)
    mode = _resolve_emoji_mode(game, mode_slug)
    daily_service = EmojiDailyTargetService(game, request.user, mode)

    if not EmojiDailyTargetService.has_clue_bank(game):
        return _render_unavailable(
            request,
            game,
            mode,
            "Aún no hay pistas emoji configuradas para este juego.",
        )

    daily_target = daily_service.resolve_playable_target()
    if not daily_target:
        return _render_unavailable(
            request,
            game,
            mode,
            "No se pudo preparar el personaje de hoy para el modo Emojis.",
        )

    context = EmojiContextBuilder(request, game, mode, daily_target).build()
    if context.get("emoji_unavailable"):
        return _render_unavailable(
            request,
            game,
            mode,
            "El personaje de hoy no tiene pistas emoji configuradas.",
        )
    return render(request, "games/play_emoji.html", context)


@require_POST
@login_required
@never_cache
@csrf_protect
def emoji_guess(request, slug: str, mode_slug: str):
    game, mode, _, _daily_target = resolve_play_context(request, slug, mode_slug)
    if not mode or not mode.is_emoji:
        raise Http404("Modo emoji no encontrado.")

    daily_target = EmojiDailyTargetService(game, request.user, mode).resolve_playable_target()
    if not daily_target:
        return JsonResponse({"error": "No daily target set."}, status=400)

    processor = EmojiGuessProcessor(game, mode, request.user)
    is_valid, payload = processor.process(request, daily_target)
    if not is_valid:
        return JsonResponse(payload, status=400)
    return JsonResponse(payload)
