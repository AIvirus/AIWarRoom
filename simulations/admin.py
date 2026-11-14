from django.contrib import admin

from .models import Scenario, SimulationResult, SimulationRun


@admin.register(Scenario)
class ScenarioAdmin(admin.ModelAdmin):
    list_display = ["name", "template_key", "business", "created_at"]
    list_filter = ["template_key"]


class ResultInline(admin.TabularInline):
    model = SimulationResult
    extra = 0
    readonly_fields = ["case_key", "label", "metrics"]
    exclude = ["timeline"]


@admin.register(SimulationRun)
class SimulationRunAdmin(admin.ModelAdmin):
    list_display = ["scenario", "status", "engine_version", "created_at"]
    readonly_fields = ["input_snapshot", "input_hash", "engine_version"]
    inlines = [ResultInline]
