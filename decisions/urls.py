from django.urls import path

from . import views

app_name = "decisions"

urlpatterns = [
    path("<uuid:pk>/brief/", views.DecisionBriefView.as_view(), name="brief"),
]
