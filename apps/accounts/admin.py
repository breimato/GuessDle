from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.contrib import admin
from apps.accounts.models import UserProfile


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


admin.site.unregister(User)
admin.site.register(User, UserAdmin)

