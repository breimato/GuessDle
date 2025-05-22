from django.urls import path
from .views import play_view
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('play/<slug:slug>/', play_view, name='play'),
]
