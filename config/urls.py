from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from accounts import api as accounts_api
from accounts import views as accounts_views

from . import views

# One router for the whole JSON API; each app registers its ViewSets here.
router = DefaultRouter()
router.register("organizations", accounts_api.OrganizationViewSet, basename="organization")

api_v1 = [
    path("me/", accounts_api.me, name="me"),
    path("", include(router.urls)),
]

urlpatterns = [
    path("", accounts_views.home, name="home"),
    path("accounts/", include("accounts.urls")),
    path("api/v1/", include((api_v1, "api"), namespace="api")),
    path("admin/", admin.site.urls),
    path("healthz/", views.healthz, name="healthz"),
]
