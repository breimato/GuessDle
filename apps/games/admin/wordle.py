from io import StringIO

from django.contrib import admin, messages
from django.core.management import call_command
from django.utils import timezone

from apps.games.admin.site import admin_site
from apps.games.models import DailyTarget, ExtraDailyPlay


@admin.register(DailyTarget, site=admin_site)
class DailyTargetAdmin(admin.ModelAdmin):
    list_display = ("game", "mode", "target", "date", "is_team")
    list_filter = ("game", "mode", "is_team", "date")
    actions = [
        "delete_selected_from_today_action",
        "delete_game_targets_from_today_action",
        "generate_daily_targets_action",
    ]

    def delete_selected_from_today_action(self, request, queryset):
        today = timezone.localdate()
        to_delete = queryset.filter(date__gte=today)
        count = to_delete.count()
        to_delete.delete()
        self.message_user(
            request,
            f"Eliminados {count} DailyTargets seleccionados con fecha >= {today}.",
            level=messages.SUCCESS,
        )

    delete_selected_from_today_action.short_description = (
        "Borrar seleccionados desde hoy"
    )

    def delete_game_targets_from_today_action(self, request, queryset):
        today = timezone.localdate()
        game_ids = queryset.values_list("game_id", flat=True).distinct()
        deleted, _ = DailyTarget.objects.filter(
            game_id__in=game_ids,
            date__gte=today,
        ).delete()
        self.message_user(
            request,
            f"Eliminados {deleted} DailyTargets desde {today} "
            f"para los juegos implicados.",
            level=messages.SUCCESS,
        )

    delete_game_targets_from_today_action.short_description = (
        "Borrar todos los DailyTargets desde hoy (juegos seleccionados)"
    )

    def generate_daily_targets_action(self, request, queryset):
        buffer = StringIO()
        call_command("generate_daily_targets", stdout=buffer)
        output = buffer.getvalue().strip()
        if output:
            preview = output if len(output) <= 2000 else output[:2000] + "\n..."
            self.message_user(request, preview)
        self.message_user(
            request,
            "Comando generate_daily_targets ejecutado.",
            level=messages.SUCCESS,
        )

    generate_daily_targets_action.short_description = (
        "Generar retos diarios hasta fin de año (todos los juegos activos)"
    )
    search_fields = ("game__name", "target__name")


@admin.register(ExtraDailyPlay, site=admin_site)
class ExtraDailyPlayAdmin(admin.ModelAdmin):
    list_display = ("user", "game", "target", "created_at", "bet_amount", "completed")
    list_filter = ("game", "completed")
    search_fields = ("user__username", "target__name")
