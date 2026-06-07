from django.contrib import admin

from apps.games.admin.site import admin_site
from apps.games.models import (
    RoscoJackpotWinner,
    RoscoLetterAttempt,
    RoscoQuestion,
    RoscoWeeklyPot,
    WeeklyRosco,
    WeeklyRoscoEntry,
)


class WeeklyRoscoEntryInline(admin.TabularInline):
    model = WeeklyRoscoEntry
    extra = 0
    readonly_fields = ("letter", "sort_order", "question", "prompt_snapshot")


@admin.register(RoscoQuestion, site=admin_site)
class RoscoQuestionAdmin(admin.ModelAdmin):
    list_display = ("game", "letter", "question_type", "category", "active", "prompt")
    list_filter = ("game", "letter", "active", "question_type")
    search_fields = ("prompt", "acceptable_answers")


@admin.register(WeeklyRosco, site=admin_site)
class WeeklyRoscoAdmin(admin.ModelAdmin):
    list_display = ("game", "mode", "week_start", "is_team", "created_at")
    list_filter = ("game", "mode", "is_team")
    inlines = [WeeklyRoscoEntryInline]


@admin.register(RoscoWeeklyPot, site=admin_site)
class RoscoWeeklyPotAdmin(admin.ModelAdmin):
    list_display = ("weekly_rosco", "pot_amount", "weekly_contribution", "rollover_amount", "settled")
    list_filter = ("settled",)


@admin.register(RoscoLetterAttempt, site=admin_site)
class RoscoLetterAttemptAdmin(admin.ModelAdmin):
    list_display = ("session", "letter", "is_correct", "answer_text", "created_at")
    list_filter = ("is_correct",)


@admin.register(RoscoJackpotWinner, site=admin_site)
class RoscoJackpotWinnerAdmin(admin.ModelAdmin):
    list_display = ("weekly_rosco", "user", "share_amount", "created_at")
    search_fields = ("user__username",)
