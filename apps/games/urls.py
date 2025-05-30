from django.urls import path

from . import views
from .views import play_view, start_extra_daily, play_extra_daily, ajax_guess_extra
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('play/<slug:slug>/', play_view, name='play'),
    path("<slug:slug>/guess/", views.ajax_guess, name="ajax_guess"),
    path("start-extra/<slug:slug>/", start_extra_daily, name="start_extra_daily"),
    path("play-extra/<int:extra_id>/", play_extra_daily, name="play_extra_daily"),
    path("ajax/guess-extra/<int:extra_id>/", ajax_guess_extra, name="ajax_guess_extra"),


]
