from django.urls import path
from django.contrib.auth import views as auth_views

from .views import (
    LoginView,
    cancel_challenge,
    dashboard_view,
    reject_challenge,
    register_view,
    complete_challenge,
    create_challenge,
)
from ..games.views import play_challenge_game, process_challenge_guess

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register_view, name='register'),
    path("challenges/create/", create_challenge, name="create_challenge"),
    path("challenges/<int:challenge_id>/play/", play_challenge_game, name="play_challenge"),
    path("challenges/<int:challenge_id>/complete/", complete_challenge, name="complete_challenge"),
    path("challenges/<int:challenge_id>/guess/", process_challenge_guess, name="ajax_guess_challenge"),
    path("challenge/<int:challenge_id>/reject/", reject_challenge, name="reject_challenge"),
    path("challenge/<int:challenge_id>/cancel/", cancel_challenge, name="cancel_challenge"),
]
