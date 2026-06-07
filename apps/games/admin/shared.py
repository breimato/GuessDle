from django.contrib import admin, messages

from apps.games.admin.site import admin_site
from apps.games.models import GameAttempt, PlaySession
from apps.games.services.admin.reset_play_service import reset_play_session


@admin.register(PlaySession, site=admin_site)
class PlaySessionAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "mode", "session_type", "reference_id", "surrendered", "completed_at")
    list_filter = ("game", "session_type", "mode__play_type", "surrendered")
    search_fields = ("user__username",)
    actions = ["reset_sessions_action"]

    @admin.action(description="Resetear partida (borrar intentos y flags)")
    def reset_sessions_action(self, request, queryset):
        total_attempts = 0
        reset_count = 0
        for session in queryset:
            deleted = reset_play_session(session)
            total_attempts += deleted
            reset_count += 1
        self.message_user(
            request,
            f"Reseteadas {reset_count} sesión(es); eliminados {total_attempts} intento(s).",
            level=messages.SUCCESS,
        )


@admin.register(GameAttempt, site=admin_site)
class GameAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "guess", "is_correct", "attempted_at", "session")
    list_filter = ("game", "is_correct", "session__session_type", "session__mode__play_type")
    search_fields = ("user__username", "guess__name")
