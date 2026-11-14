from django.contrib import admin

from .models import BusinessComponent, BusinessProfile, FinancialAssumption


class AssumptionInline(admin.TabularInline):
    model = FinancialAssumption
    extra = 0
    readonly_fields = ["unit"]


@admin.register(BusinessProfile)
class BusinessProfileAdmin(admin.ModelAdmin):
    list_display = ["name", "mode", "organization", "archived_at"]
    list_filter = ["mode"]
    inlines = [AssumptionInline]


@admin.register(BusinessComponent)
class BusinessComponentAdmin(admin.ModelAdmin):
    list_display = ["name", "kind", "business", "criticality"]
    filter_horizontal = ["depends_on"]
