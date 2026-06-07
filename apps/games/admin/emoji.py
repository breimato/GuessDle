from django.contrib import admin

from apps.games.admin.site import admin_site
from apps.games.models import EmojiClueSet


@admin.register(EmojiClueSet, site=admin_site)
class EmojiClueSetAdmin(admin.ModelAdmin):
    list_display = ("game", "item", "clue_count", "active", "updated_at")
    list_filter = ("game", "active")
    search_fields = ("item__name",)
    readonly_fields = ("created_at", "updated_at")

    @admin.display(description="Pistas")
    def clue_count(self, obj):
        return len(obj.clues or [])
