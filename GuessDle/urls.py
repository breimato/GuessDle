from django.contrib import admin
from django.urls import path, include

from apps.games.views import ranking_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('home/', include('apps.accounts.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('games/', include('apps.games.urls')),
    path("ranking/", ranking_view, name="ranking_global"),
    path("ranking/<slug:slug>/", ranking_view, name="ranking_game"),
]
