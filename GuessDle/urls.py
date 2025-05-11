from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/', include('apps.accounts.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('games/', include('apps.games.urls')),
]
