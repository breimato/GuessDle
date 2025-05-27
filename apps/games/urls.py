from django.urls import path

from . import views
from .views import play_view
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('play/<slug:slug>/', play_view, name='play'),
    path("<slug:slug>/guess/", views.ajax_guess, name="ajax_guess"),

]
