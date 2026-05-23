from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.timezone import now
from django.views.decorators.cache import never_cache
from django.contrib import messages
from django.db import models
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.models import User
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template.loader import render_to_string

from apps.accounts.models import Challenge
from apps.accounts.services.dashboard_stats import DashboardStats
from apps.games.models import ExtraDailyPlay
from apps.games.services.gameplay.target_service import TargetService
from apps.games.services.gameplay.challenge_view_helper import ChallengeViewHelper
from apps.games.services.gameplay.challenge_resolution_service import ChallengeResolutionService
from apps.common.utils import json_success, json_error


@login_required
@csrf_protect
def create_challenge(request):
    """Create a new 1v1 challenge via POST request."""

    challenge, error_message = ChallengeViewHelper.create_challenge(request)
    if error_message:
        return json_error(error_message)

    card_html = render_to_string(
        "partials/sent_challenge_card.html",
        {"challenge": challenge},
        request=request
    )
    return json_success({"card": card_html})


@require_POST
@login_required
def cancel_challenge(request, challenge_id):
    """Cancel a pending challenge created by the user."""

    is_cancelled = ChallengeViewHelper.cancel_challenge(request, challenge_id)
    if not is_cancelled:
        return json_error("Could not cancel challenge")
    return json_success({"id": challenge_id})


@require_POST
@login_required
def reject_challenge(request, challenge_id):
    """Reject a pending challenge received by the user."""

    is_rejected = ChallengeViewHelper.reject_challenge(request, challenge_id)
    if not is_rejected:
        return json_error("Could not reject challenge")
    return json_success({"id": challenge_id})


@never_cache
@login_required
def dashboard_view(request):
    """Render the main statistics dashboard for the authenticated user."""

    stats = DashboardStats(request.user)
    users = User.objects.exclude(id=request.user.id)

    pending_challenges = Challenge.objects.filter(opponent=request.user, accepted=False)
    active_challenges = Challenge.objects.filter(
        accepted=True,
        completed=False
    ).filter(models.Q(challenger=request.user) | models.Q(opponent=request.user))
    active_challenges_to_play = Challenge.objects.filter(
        accepted=True,
        completed=False,
        challenger=request.user
    )

    sent_pending_challenges = Challenge.objects.filter(
        challenger=request.user,
        accepted=False,
        completed=False
    )

    today = now().date()
    active_extras = ExtraDailyPlay.objects.filter(
        user=request.user,
        completed=False,
        created_at__date=today
    ).select_related('game')

    extras_by_slug = {extra.game.slug: extra.id for extra in active_extras}

    available_games = stats.fetch_active_games()
    daily_targets_by_slug = {
        game.slug: bool(not TargetService(game, request.user).is_daily_resolved())
        for game in available_games
    }

    for game in available_games:
        if daily_targets_by_slug.get(game.slug):
            game.redirect_url = reverse("play", args=[game.slug])
        elif game.slug in extras_by_slug:
            game.redirect_url = reverse("play_extra_daily", args=[extras_by_slug[game.slug]])
        else:
            game.redirect_url = reverse("play", args=[game.slug])

    context = {
        "available_games": available_games,
        "user_stats": {
            "games": stats.calculate_user_statistics(),
            "global_elo": stats.calculate_global_elo_score(),
        },
        "global_ranking": stats.generate_global_ranking(),
        "ranking_by_game": stats.generate_ranking_per_game(),
        "pending_challenges": pending_challenges,
        "active_challenges": active_challenges,
        "active_challenges_to_play": active_challenges_to_play,
        "sent_pending_challenges": sent_pending_challenges,
        "users": users,
    }

    return render(request, "accounts/dashboard.html", context)


def register_view(request):
    """Handle new user registration via standard form submission."""

    if request.method != "POST":
        return render(request, "accounts/register.html")

    username = request.POST.get("username")
    first_name = request.POST.get("first_name")
    email = request.POST.get("email")
    password = request.POST.get("password1")
    confirm_password = request.POST.get("password2")
    is_team_account = request.POST.get("is_team_account") == "on"

    for field in [username, first_name, email, password, confirm_password]:
        if not field or field.strip() == "":
            messages.error(request, "All fields are required.")
            return render(request, "accounts/register.html")

    try:
        validate_email(email)
    except ValidationError:
        messages.error(request, "Invalid email format.")
        return render(request, "accounts/register.html")

    if password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return render(request, "accounts/register.html")

    if User.objects.filter(username=username).exists():
        messages.error(request, "This nickname is already taken.")
        return render(request, "accounts/register.html")

    if User.objects.filter(email=email).exists():
        messages.error(request, "There is already an account with this email.")
        return render(request, "accounts/register.html")

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        email=email,
        password=password
    )

    user.profile.is_team_account = is_team_account
    user.profile.save()

    messages.success(request, "Registration complete! Please log in.")
    return redirect("login")


@login_required
@csrf_protect
def complete_challenge(request, challenge_id):
    """Complete a challenge and resolve point allocations."""

    challenge = get_object_or_404(Challenge, pk=challenge_id, accepted=True, completed=False)
    result = ChallengeResolutionService(challenge, acting_user=request.user).resolve_and_assign_points()

    if result["status"] == "already-resolved":
        return JsonResponse({"status": "already-resolved"})
    if result["status"] == "tie":
        return JsonResponse({
            "status": "tie",
            "users": [user.username for user in result["users"]],
        })
    if result["status"] == "winner":
        return JsonResponse({
            "status": "success",
            "winner": result["winner"].username,
            "loser": result["loser"].username,
        })
    return JsonResponse({"status": "error"})


class LoginView(DjangoLoginView):
    """Custom LoginView that supports 'Remember Me' sessions."""

    template_name = "registration/login.html"

    def form_valid(self, form):
        """Configure session expiry when the login form is successfully submitted."""

        response = super().form_valid(form)
        remember_me = self.request.POST.get('remember_me')

        if remember_me:
            self.request.session.set_expiry(1209600)
        else:
            self.request.session.set_expiry(0)

        return response
