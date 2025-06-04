from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib import admin
from apps.accounts.models import UserProfile, GameElo, Challenge
from django.db.models import F



class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "Perfil adicional"
    fk_name = "user"


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

    def is_team_account(self, obj):
        return getattr(obj.profile, "is_team_account", False)

    is_team_account.boolean = True
    is_team_account.short_description = "Cuenta de equipo"

    def get_list_display(self, request):
        return super().get_list_display(request) + ('is_team_account',)


@admin.register(GameElo)
class GameEloAdmin(admin.ModelAdmin):
    list_display = ('user', 'game', 'elo', 'partidas')
    list_filter = ('game',)
    search_fields = ('user__username',)
    list_editable = ('elo',)   # Puedes editar el ELO directamente en la lista

    actions = ['sumar_elo']

    @admin.action(description="Sumar 50 puntos de elo a los seleccionados")
    def sumar_elo(self, request, queryset):
        updated = queryset.update(elo=F('elo') + 50)
        self.message_user(request, f"Sumados 50 puntos de elo a {updated} usuarios.")

@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ('challenger', 'opponent', 'game', 'target', 'created_at', 'accepted', 'completed', 'winner', 'elo_exchanged')
    list_filter = ('game', 'accepted', 'completed')
    search_fields = ('challenger__username', 'opponent__username', 'target__name')

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

