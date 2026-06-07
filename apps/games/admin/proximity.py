from django.contrib import admin, messages
from django.utils import timezone

from apps.games.admin.site import admin_site
from apps.games.models import ProximityAttempt, ProximityDailyAssignment, ProximityPrompt
from apps.games.services.admin.reset_play_service import (
    delete_proximity_assignments,
    reset_proximity_assignment,
)


@admin.register(ProximityPrompt, site=admin_site)
class ProximityPromptAdmin(admin.ModelAdmin):
    list_display = ("game", "prompt_text", "answer_value", "answer_episode", "kind", "active")
    list_filter = ("game", "kind", "active")
    search_fields = ("prompt_text",)


@admin.register(ProximityDailyAssignment, site=admin_site)
class ProximityDailyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "mode", "date", "answer_value", "is_team")
    list_filter = ("game", "mode", "date", "is_team")
    readonly_fields = ("created_at",)
    actions = [
        "reset_sessions_action",
        "delete_with_sessions_action",
        "delete_from_today_by_game_action",
    ]

    @admin.action(description="Resetear partidas (mantener assignment)")
    def reset_sessions_action(self, request, queryset):
        reset_count = 0
        for assignment in queryset:
            reset_proximity_assignment(assignment)
            reset_count += 1
        self.message_user(
            request,
            f"Reseteadas {reset_count} assignment(s) de Proximidad (sesiones e intentos borrados).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Borrar assignments y sesiones asociadas")
    def delete_with_sessions_action(self, request, queryset):
        deleted = delete_proximity_assignments(queryset)
        self.message_user(
            request,
            f"Eliminados {deleted} assignment(s) de Proximidad y sus sesiones.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Borrar assignments desde hoy (juegos seleccionados)")
    def delete_from_today_by_game_action(self, request, queryset):
        today = timezone.localdate()
        game_ids = queryset.values_list("game_id", flat=True).distinct()
        to_delete = ProximityDailyAssignment.objects.filter(
            game_id__in=game_ids,
            date__gte=today,
        )
        deleted = delete_proximity_assignments(to_delete)
        self.message_user(
            request,
            f"Eliminados {deleted} ProximityDailyAssignment(s) desde {today}.",
            level=messages.SUCCESS,
        )


@admin.register(ProximityAttempt, site=admin_site)
class ProximityAttemptAdmin(admin.ModelAdmin):
    list_display = ("session", "guess_value", "distance", "created_at")
    list_filter = ("session__game", "session__session_type")
