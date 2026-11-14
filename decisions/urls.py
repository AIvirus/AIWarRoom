from django.urls import path

from . import views

app_name = "decisions"

urlpatterns = [
    path("<uuid:pk>/brief/", views.DecisionBriefView.as_view(), name="brief"),
    path("<uuid:pk>/status/", views.decision_status, name="status"),
    path("from-run/<uuid:run_pk>/", views.decision_create, name="create"),
]
