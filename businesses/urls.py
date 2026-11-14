from django.urls import path

from . import views

urlpatterns = [
    path("new/", views.business_create, name="business-create"),
    path("<uuid:pk>/", views.business_detail, name="business-detail"),
    path("<uuid:pk>/assumptions/", views.assumptions_update, name="business-assumptions"),
    path("<uuid:pk>/components/", views.component_create, name="business-component-create"),
    path(
        "<uuid:pk>/components/<uuid:component_pk>/delete/",
        views.component_delete,
        name="business-component-delete",
    ),
    path("<uuid:pk>/scenarios/", views.scenario_create, name="business-scenario-create"),
    path(
        "<uuid:pk>/scenarios/<uuid:scenario_pk>/run/",
        views.scenario_run,
        name="business-scenario-run",
    ),
]
