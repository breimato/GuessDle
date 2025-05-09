from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic.base import RedirectView
from django.urls import reverse_lazy

urlpatterns = [
    path('', RedirectView.as_view(url=reverse_lazy('login'), permanent=False)),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
