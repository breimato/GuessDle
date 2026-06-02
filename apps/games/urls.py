from django.urls import path

from .views import (
    play_daily_game,
    process_daily_guess,
    reveal_daily_hint,
    start_extra_daily_game,
    play_extra_daily_game,
    process_extra_guess,
    reveal_extra_hint,
    surrender_daily_game,
    surrender_extra_game,
    play_rosco_game,
    rosco_answer,
    rosco_pass,
    rosco_surrender,
    play_emoji_game,
    emoji_guess,
)


urlpatterns = [
    path("play/<slug:slug>/", play_daily_game, name="play"),
    path("play/<slug:slug>/<slug:mode_slug>/", play_daily_game, name="play_mode"),
    path("<slug:slug>/guess/", process_daily_guess, name="ajax_guess"),
    path("<slug:slug>/<slug:mode_slug>/guess/", process_daily_guess, name="ajax_guess_mode"),
    path("<slug:slug>/reveal-hint/", reveal_daily_hint, name="ajax_reveal_hint"),
    path("<slug:slug>/<slug:mode_slug>/reveal-hint/", reveal_daily_hint, name="ajax_reveal_hint_mode"),
    path("<slug:slug>/surrender/", surrender_daily_game, name="ajax_surrender"),
    path("<slug:slug>/<slug:mode_slug>/surrender/", surrender_daily_game, name="ajax_surrender_mode"),
    path("start-extra/<slug:slug>/", start_extra_daily_game, name="start_extra_daily"),
    path("start-extra/<slug:slug>/<slug:mode_slug>/", start_extra_daily_game, name="start_extra_daily_mode"),
    path("play-extra/<int:extra_id>/", play_extra_daily_game, name="play_extra_daily"),
    path("ajax/guess-extra/<int:extra_id>/", process_extra_guess, name="ajax_guess_extra"),
    path("ajax/reveal-hint-extra/<int:extra_id>/", reveal_extra_hint, name="ajax_reveal_hint_extra"),
    path("ajax/surrender-extra/<int:extra_id>/", surrender_extra_game, name="ajax_surrender_extra"),
    path("<slug:slug>/<slug:mode_slug>/rosco/answer/", rosco_answer, name="rosco_answer"),
    path("<slug:slug>/<slug:mode_slug>/rosco/pass/", rosco_pass, name="rosco_pass"),
    path("<slug:slug>/<slug:mode_slug>/rosco/surrender/", rosco_surrender, name="rosco_surrender"),
    path("<slug:slug>/<slug:mode_slug>/emoji/guess/", emoji_guess, name="emoji_guess"),
]
