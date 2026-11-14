from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("signup/", views.signup, name="signup"),
    # Django only accepts POST for logout, so a stray link or image can't log you out.
    path("logout/", LogoutView.as_view(), name="logout"),
]
