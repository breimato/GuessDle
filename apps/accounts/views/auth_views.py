from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.shortcuts import redirect, render

REMEMBER_ME_SESSION_AGE = 1209600
REMEMBER_ME_SESSION_KEY = "remember_me"


def has_remember_me_session(request) -> bool:
    return bool(request.session.get(REMEMBER_ME_SESSION_KEY, False))


def home_redirect(request):
    if request.user.is_authenticated and has_remember_me_session(request):
        return redirect("dashboard")
    return redirect("login")


def register_view(request):
    if request.method != "POST":
        return render(request, "accounts/register.html")

    username = request.POST.get("username")
    first_name = request.POST.get("first_name")
    password = request.POST.get("password1")
    confirm_password = request.POST.get("password2")
    is_team_account = request.POST.get("is_team_account") == "on"

    for field in [username, first_name, password, confirm_password]:
        if not field or field.strip() == "":
            messages.error(request, "All fields are required.")
            return render(request, "accounts/register.html")

    if password != confirm_password:
        messages.error(request, "Passwords do not match.")
        return render(request, "accounts/register.html")

    if User.objects.filter(username=username).exists():
        messages.error(request, "This nickname is already taken.")
        return render(request, "accounts/register.html")

    user = User.objects.create_user(
        username=username,
        first_name=first_name,
        email="",
        password=password,
    )

    user.profile.is_team_account = is_team_account
    user.profile.save()

    messages.success(request, "Registration complete! Please log in.")
    return redirect("login")


class LoginView(DjangoLoginView):
    template_name = "registration/login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and has_remember_me_session(request):
            return redirect(self.get_success_url())
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        remember_me = self.request.POST.get("remember_me")

        if remember_me:
            self.request.session.set_expiry(REMEMBER_ME_SESSION_AGE)
            self.request.session[REMEMBER_ME_SESSION_KEY] = True
        else:
            self.request.session.set_expiry(0)
            self.request.session[REMEMBER_ME_SESSION_KEY] = False

        self.request.session.modified = True
        return response
