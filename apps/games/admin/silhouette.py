from django.contrib import admin, messages
from django.utils import timezone

from apps.games.admin.site import admin_site
from apps.games.models import SilhouetteDailyAssignment
from apps.games.services.admin.reset_play_service import (
    delete_silhouette_assignments,
    reset_silhouette_assignment,
)


@admin.register(SilhouetteDailyAssignment, site=admin_site)
class SilhouetteDailyAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "mode", "date", "target_item", "anchor", "is_team")
    list_filter = ("game", "mode", "date", "is_team", "anchor")
    search_fields = ("user__username", "target_item__name")
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
            reset_silhouette_assignment(assignment)
            reset_count += 1
        self.message_user(
            request,
            f"Reseteadas {reset_count} assignment(s) de Silueta (sesiones e intentos borrados).",
            level=messages.SUCCESS,
        )

    @admin.action(description="Borrar assignments y sesiones asociadas")
    def delete_with_sessions_action(self, request, queryset):
        deleted = delete_silhouette_assignments(queryset)
        self.message_user(
            request,
            f"Eliminados {deleted} assignment(s) de Silueta y sus sesiones.",
            level=messages.SUCCESS,
        )

    @admin.action(description="Borrar assignments desde hoy (juegos seleccionados)")
    def delete_from_today_by_game_action(self, request, queryset):
        today = timezone.localdate()
        game_ids = queryset.values_list("game_id", flat=True).distinct()
        to_delete = SilhouetteDailyAssignment.objects.filter(
            game_id__in=game_ids,
            date__gte=today,
        )
        deleted = delete_silhouette_assignments(to_delete)
        self.message_user(
            request,
            f"Eliminados {deleted} SilhouetteDailyAssignment(s) desde {today}.",
            level=messages.SUCCESS,
        )
