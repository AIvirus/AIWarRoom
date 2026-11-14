from django.contrib import admin

from .models import AIAnalysis, Alert, CompanyScan


@admin.register(AIAnalysis)
class AIAnalysisAdmin(admin.ModelAdmin):
    list_display = ["kind", "status", "business", "model_name", "created_at"]
    list_filter = ["kind", "status"]


@admin.register(CompanyScan)
class CompanyScanAdmin(admin.ModelAdmin):
    list_display = ["url", "status", "business", "created_at"]


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ["summary", "severity", "kind", "business", "acknowledged_at"]
    list_filter = ["severity", "kind"]
