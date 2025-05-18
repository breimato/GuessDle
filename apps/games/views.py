from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from apps.games.models import Game
from django.contrib import messages


from apps.games.services.gameplay import get_current_target, process_guess, build_context

@never_cache
@login_required
@csrf_protect
def play_view(request, slug):
    game = get_object_or_404(Game, slug=slug)
    target, daily = get_current_target(game)

    if request.method == "POST" and build_context(request, game, daily)["can_play"]:
        valid, correct = process_guess(request, game, daily)
        if not valid:
            messages.error(request, "Intento inválido o repetido.")
        return redirect("play", slug=slug)

    ctx = build_context(request, game, daily)
    ctx["background_url"] = game.background_image.url if game.background_image else None


    return render(request, "games/play.html", ctx)



