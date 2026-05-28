from apps.accounts.views.auth_views import LoginView, register_view
from apps.accounts.views.challenge_views import (
    accept_challenge,
    cancel_challenge,
    complete_challenge,
    create_challenge,
    reject_challenge,
)
from apps.accounts.views.dashboard_views import dashboard_view
from apps.accounts.views.notification_views import notifications_ack, notifications_poll

__all__ = [
    "LoginView",
    "register_view",
    "dashboard_view",
    "notifications_poll",
    "notifications_ack",
    "create_challenge",
    "cancel_challenge",
    "reject_challenge",
    "accept_challenge",
    "complete_challenge",
]
