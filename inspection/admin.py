from django.contrib import admin
from .models import (
    Product,
    InspectionBatch,
    Inspection,
    InspectionReview,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("product_id", "name", "is_active")
    search_fields = ("product_id", "name")
    list_filter = ("is_active",)


@admin.register(InspectionBatch)
class InspectionBatchAdmin(admin.ModelAdmin):
    list_display = (
        "id", "product", "submitted_by",
        "status", "total_files", "created_at"
    )
    list_filter = ("status", "created_at")


@admin.register(Inspection)
class InspectionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "product", "predicted_class",
        "confidence", "status", "created_at"
    )
    list_filter = ("status", "predicted_class")


@admin.register(InspectionReview)
class InspectionReviewAdmin(admin.ModelAdmin):
    list_display = (
        "inspection", "reviewed_class",
        "reviewer", "reviewed_at"
    )