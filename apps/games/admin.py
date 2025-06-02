from django.contrib import admin
from .models import Game
from .models import GameItem

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'color', 'active', 'created_at')
    search_fields = ('name', 'slug', 'color')
    list_filter = ('active',)
    prepopulated_fields = {"slug": ("name",)}
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'description', 'active')
        }),
        ('Visuals', {
            'fields': ('color', 'icon_image', 'background_image')
        }),
        ('API Configuration', {
            'fields': ('data_source_url', 'field_mapping', 'defaults', 'attributes', 'numeric_fields', 'audio_file')
        }),
    )


@admin.register(GameItem)
class GameItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'game')
    list_filter = ('game',)
    search_fields = ('name',)
