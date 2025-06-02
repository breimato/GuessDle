from django.contrib import admin
from .models import Game
from .models import GameItem
from django.contrib import admin
from apps.games.models import ScoringRule

@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'active', 'created_at')
    search_fields = ('name', 'slug')
    list_filter = ('active',)
    prepopulated_fields = {"slug": ("name",)}


@admin.register(GameItem)
class GameItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'game')
    list_filter = ('game',)
    search_fields = ('name',)


@admin.register(ScoringRule)
class ScoringRuleAdmin(admin.ModelAdmin):
    list_display  = ("game", "attempt_no", "points")
    list_filter   = ("game",)
    ordering      = ("game", "attempt_no")

