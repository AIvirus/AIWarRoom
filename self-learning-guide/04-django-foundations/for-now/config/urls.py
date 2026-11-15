from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from accounts import api as accounts_api

from . import views

# One router for the whole JSON API; each app's ViewSets are registered here.
router = DefaultRouter()
router.register("organizations", accounts_api.OrganizationViewSet, basename="organization")

api_v1 = [
    path("me/", accounts_api.me, name="me"),
    path("", include(router.urls)),
]

urlpatterns = [
    # A temporary home page. Part 10 replaces it with the real operations board.
    path("", login_required(TemplateView.as_view(template_name="home.html")), name="home"),
    path("accounts/", include("accounts.urls")),
    path("api/v1/", include((api_v1, "api"), namespace="api")),
    path("admin/", admin.site.urls),
    path("healthz/", views.healthz, name="healthz"),
]
