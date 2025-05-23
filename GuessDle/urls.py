from django.contrib import admin
from django.shortcuts import redirect
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.urls import reverse_lazy

urlpatterns = [
    path('', lambda request: redirect(reverse_lazy('login'))),
    path('admin/', admin.site.urls),
    path('home/', include('apps.accounts.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('games/', include('apps.games.urls')),

]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
