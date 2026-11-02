from django.contrib import admin
from django.db.models import Count
from manuals.models import Manual
from .models import Machine


class ManualInline(admin.TabularInline):
    model = Manual
    fields = ("document_id", "title", "revision", "indexing_status", "uploaded_at")
    readonly_fields = ("uploaded_at",)
    extra = 0
    show_change_link = True


@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "model_number",
        "is_active",
        "manuals_count_display",
        "created_at",
    )
    list_filter = ("is_active", "created_at")
    search_fields = ("name", "model_number", "description")
    list_editable = ("is_active",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [ManualInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(annotated_manuals_count=Count("manuals"))

    @admin.display(description="Linked Manuals", ordering="annotated_manuals_count")
    def manuals_count_display(self, obj):
        return getattr(obj, "annotated_manuals_count", obj.manuals.count())
