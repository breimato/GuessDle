from django.urls import path
from django.contrib.auth import views as auth_views

from .views import (
    LoginView,
    PasswordResetView,
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
    path("password_reset/", PasswordResetView.as_view(), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html"
    ), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html"
    ), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html"
    ), name="password_reset_complete"),
    path("challenges/create/", create_challenge, name="create_challenge"),
    path("challenges/<int:challenge_id>/play/", play_challenge_game, name="play_challenge"),
    path("challenges/<int:challenge_id>/complete/", complete_challenge, name="complete_challenge"),
    path("challenges/<int:challenge_id>/guess/", process_challenge_guess, name="ajax_guess_challenge"),
    path("challenge/<int:challenge_id>/reject/", reject_challenge, name="reject_challenge"),
    path("challenge/<int:challenge_id>/cancel/", cancel_challenge, name="cancel_challenge"),
]
