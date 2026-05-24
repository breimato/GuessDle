from django.urls import path

from .views import (
    play_daily_game,
    process_daily_guess,
    reveal_daily_hint,
    start_extra_daily_game,
    play_extra_daily_game,
    process_extra_guess,
    reveal_extra_hint,
)


urlpatterns = [
    path('play/<slug:slug>/', play_daily_game, name='play'),
    path("<slug:slug>/guess/", process_daily_guess, name="ajax_guess"),
    path("<slug:slug>/reveal-hint/", reveal_daily_hint, name="ajax_reveal_hint"),
    path("start-extra/<slug:slug>/", start_extra_daily_game, name="start_extra_daily"),
    path("play-extra/<int:extra_id>/", play_extra_daily_game, name="play_extra_daily"),
    path("ajax/guess-extra/<int:extra_id>/", process_extra_guess, name="ajax_guess_extra"),
    path("ajax/reveal-hint-extra/<int:extra_id>/", reveal_extra_hint, name="ajax_reveal_hint_extra"),
]
