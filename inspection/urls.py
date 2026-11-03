from django.urls import path
from . import views

app_name = "inspection"

urlpatterns = [
    # Administrator Operations: Supported Products Management
    path(
        "products/",
        views.product_list,
        name="product_list"
    ),
    path(
        "products/create/",
        views.product_create,
        name="product_create"
    ),
    path(
        "products/<int:pk>/edit/",
        views.product_edit,
        name="product_edit"
    ),
    path(
        "products/<int:pk>/toggle/",
        views.product_toggle_status,
        name="product_toggle"
    ),

    # Engineer Operations: Single & Batch Visual Quality Inspection
    path(
        "upload/",
        views.upload_inspection,
        name="upload_inspection"
    ),
    path(
        "detail/<int:pk>/",
        views.inspection_detail,
        name="inspection_detail"
    ),
    path(
        "history/",
        views.inspection_history,
        name="inspection_history"
    ),
    path(
        "batch/upload/",
        views.batch_upload,
        name="batch_upload"
    ),
    path(
        "batch/<int:pk>/",
        views.batch_detail,
        name="batch_detail"
    ),
    path(
        "batch/<int:pk>/process-next/",
        views.batch_process_next,
        name="batch_process_next"
    ),
    path(
        "batch/<int:pk>/status/",
        views.batch_status,
        name="batch_status"
    ),

    # Supervisor Operations: Prediction Confirmation & Correction
    path(
        "review/<int:pk>/",
        views.review_inspection,
        name="review_inspection"
    ),

    # Benchmark Model Evaluation (Supervisor & Administrator)
    path(
        "evaluation/",
        views.model_evaluation,
        name="model_evaluation"
    ),
]
