from django.contrib import admin
from .models import Manual


@admin.register(Manual)
class ManualAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "document_id",
        "machine",
        "revision",
        "indexing_status",
        "uploaded_at",
    )

    list_filter = (
        "machine",
        "indexing_status",
        "revision",
    )

    search_fields = (
        "title",
        "document_id",
        "machine__model_number",
    )

    readonly_fields = (
        "indexing_status",
        "total_pages",
        "total_chunks",
        "uploaded_at",
        "updated_at",
    )