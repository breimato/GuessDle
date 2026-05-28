from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache

from apps.accounts.services.dashboard.dashboard_context import build_dashboard_context
from apps.accounts.services.notifications.notification_service import NotificationService


@never_cache
@login_required
def dashboard_view(request):
    NotificationService.migrate_legacy_unread(request.user)
    context = build_dashboard_context(request)
    return render(request, "accounts/dashboard.html", context)
