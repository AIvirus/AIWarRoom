from django.contrib import admin

from .models import Decision


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = ["title", "status", "owner", "business", "created_at"]
    list_filter = ["status"]
