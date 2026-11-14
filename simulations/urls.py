from django.urls import path

from . import views

urlpatterns = [
    path("<uuid:pk>/", views.run_detail, name="run-detail"),
]
