from django.urls import path
from .views import LoginView, cancelar_challenge, dashboard_view, rechazar_challenge, register_view, complete_challenge, create_challenge
from django.contrib.auth import views as auth_views

from ..games.views import play_challenge, ajax_guess_challenge

urlpatterns = [
    path('', dashboard_view, name='dashboard'),
    path('login/', LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', register_view, name='register'),
    path("password_reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset_form.html"
    ), name="password_reset"),

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
    path("challenges/<int:challenge_id>/play/", play_challenge, name="play_challenge"),
    path("challenges/<int:challenge_id>/complete/", complete_challenge, name="complete_challenge"),
    path("challenges/<int:challenge_id>/guess/", ajax_guess_challenge, name="ajax_guess_challenge"),
    path('challenge/<int:challenge_id>/rechazar/', rechazar_challenge, name='rechazar_challenge'),
    path("challenge/<int:challenge_id>/cancel/", cancelar_challenge, name="cancelar_challenge"),

]
