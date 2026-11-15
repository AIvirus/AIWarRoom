from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.urls import include, path
from django.views.generic import TemplateView
from rest_framework.routers import DefaultRouter

from accounts import api as accounts_api
from businesses import api as businesses_api
from decisions import api as decisions_api
from intelligence import api as intelligence_api
from intelligence import views as intelligence_views
from simulations import api as simulations_api

from . import views

# One router for the whole JSON API; each app's ViewSets are registered here.
router = DefaultRouter()
router.register("organizations", accounts_api.OrganizationViewSet, basename="organization")
router.register("businesses", businesses_api.BusinessViewSet, basename="business")
router.register("scenarios", simulations_api.ScenarioViewSet, basename="scenario")
router.register("runs", simulations_api.SimulationRunViewSet, basename="run")
router.register("analyses", intelligence_api.AIAnalysisViewSet, basename="analysis")
router.register("scans", intelligence_api.CompanyScanViewSet, basename="scan")
router.register("alerts", intelligence_api.AlertViewSet, basename="alert")
router.register("decisions", decisions_api.DecisionViewSet, basename="decision")

# Components live under their business: /businesses/<id>/components/. Wired by hand
# (rather than a nested-router package) so the mapping is visible.
components_list = businesses_api.ComponentViewSet.as_view({"get": "list", "post": "create"})
components_detail = businesses_api.ComponentViewSet.as_view(
    {"get": "retrieve", "patch": "partial_update", "delete": "destroy"}
)

api_v1 = [
    path("me/", accounts_api.me, name="me"),
    path("scenario-templates/", simulations_api.scenario_templates, name="scenario-templates"),
    path("inputs/", simulations_api.input_catalog, name="inputs"),
    path("simulate/preview/", simulations_api.simulate_preview, name="simulate-preview"),
    path("scans/<uuid:pk>/events/", intelligence_views.scan_events, name="scan-events"),
    path("businesses/<uuid:business_pk>/components/", components_list, name="component-list"),
    path(
        "businesses/<uuid:business_pk>/components/<uuid:pk>/",
        components_detail,
        name="component-detail",
    ),
    path("", include(router.urls)),
]

urlpatterns = [
    # A temporary home page. Part 10 replaces it with the real operations board.
    path("", login_required(TemplateView.as_view(template_name="home.html")), name="home"),
    path("accounts/", include("accounts.urls")),
    path("decisions/", include("decisions.urls")),
    path("api/v1/", include((api_v1, "api"), namespace="api")),
    path("admin/", admin.site.urls),
    path("healthz/", views.healthz, name="healthz"),
]
