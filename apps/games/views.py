# apps/games/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from apps.games.models import Game, GameItem
from apps.games.session import GameSession
from apps.games.services.gameplay import process_guess, build_context


@never_cache
@login_required
@csrf_protect
def play_view(request, slug):
    """Orquesta la partida; la lógica viva está en services/."""
    game = get_object_or_404(Game, slug=slug)
    sess = GameSession(request.session)

    # objetivo actual o nuevo
    if sess.target_id and sess.target_game == game.id:
        target = GameItem.objects.get(id=sess.target_id)
    else:
        target = sess.start_new(game)

    # --- POST → delega a service, luego redirige (PRG) -----------------
    if request.method == "POST":
        process_guess(request, game, sess, target)
        return redirect("play", slug=slug)

    # --- GET → solo construir contexto y renderizar --------------------
    ctx = build_context(game, sess, target)

    # añade la URL del fondo del juego (o None)
    ctx["background_url"] = game.background_image.url if game.background_image else None

    return render(request, "games/play.html", ctx)


