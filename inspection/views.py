from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, F
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.permissions import (
    administrator_required,
    supervisor_required,
    engineer_required,
    is_administrator,
    is_supervisor,
    is_engineer,
    get_user_roles,
)
from .forms import ProductForm, InspectionUploadForm, InspectionReviewForm
from .models import Product, Inspection, InspectionBatch, InspectionReview
from .services import process_single_inspection
from .validators import validate_inspection_image
from .evaluation import evaluate_model


def is_inspection_supervisor(user):
    """
    Check if the user specifically holds the Supervisor role for Quality Assurance review.
    Pure Administrators are restricted to Product Catalog management.
    """
    if not user.is_authenticated:
        return False
    roles = get_user_roles(user)
    if "Supervisor" in roles:
        return True
    if user.is_superuser and "Administrator" not in roles:
        return True
    return False


# ============================================================================
# Administrator Operations: Supported Products Management
# ============================================================================

@administrator_required
def product_list(request):
    """
    Displays the catalog of supported products (e.g. P-PLATE01) with aggregated telemetry.
    """
    products = Product.objects.all().order_by("product_id")
    product_stats = []

    for prod in products:
        inspections = prod.inspections.all()
        total_eval = inspections.count()
        normal_eval = inspections.filter(predicted_class="Normal").count()
        defect_eval = inspections.filter(predicted_class="Defective").count()
        product_stats.append({
            "product": prod,
            "total_inspections": total_eval,
            "normal_count": normal_eval,
            "defective_count": defect_eval,
        })

    return render(
        request,
        "inspection/product_list.html",
        {
            "product_stats": product_stats,
            "total_products": products.count(),
            "active_products": products.filter(is_active=True).count(),
        }
    )


@administrator_required
def product_create(request):
    """
    Administrator registers a supported product (e.g., P-PLATE01).
    """
    if request.method == "POST":
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            messages.success(
                request,
                f"Supported product {product.product_id} ('{product.name}') registered successfully."
            )
            return redirect("inspection:product_list")
    else:
        # Check if P-PLATE01 is already registered, otherwise offer as suggestion
        initial_id = "P-PLATE01" if not Product.objects.filter(product_id="P-PLATE01").exists() else ""
        initial_name = "Demonstration metal plate" if initial_id else ""
        form = ProductForm(initial={"product_id": initial_id, "name": initial_name, "is_active": True})

    return render(
        request,
        "inspection/product_create.html",
        {
            "form": form,
            "is_edit": False,
        }
    )


@administrator_required
def product_edit(request, pk):
    """
    Administrator edits an existing supported product.
    """
    product = get_object_or_404(Product, pk=pk)
    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(
                request,
                f"Product {product.product_id} specifications updated."
            )
            return redirect("inspection:product_list")
    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "inspection/product_create.html",
        {
            "form": form,
            "product": product,
            "is_edit": True,
        }
    )


@administrator_required
def product_toggle_status(request, pk):
    """
    Administrator toggles active/inactive status of a product.
    """
    if request.method == "POST":
        product = get_object_or_404(Product, pk=pk)
        product.is_active = not product.is_active
        product.save(update_fields=["is_active"])
        state = "activated" if product.is_active else "deactivated"
        messages.success(request, f"Product {product.product_id} has been {state}.")
    return redirect("inspection:product_list")


# ============================================================================
# Engineer Operations: Single Visual Quality Inspection
# ============================================================================

@engineer_required
def upload_inspection(request):
    """
    Engineer selects a product and uploads a JPG or PNG optical capture.
    The application runs model inference and displays the diagnostic result.
    Restricted to Engineer role.
    """
    if is_inspection_supervisor(request.user) or is_administrator(request.user):
        raise PermissionDenied("Component image upload is restricted exclusively to the Engineer role.")

    if request.method == "POST":
        form = InspectionUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():
            inspection = form.save(commit=False)
            inspection.submitted_by = request.user
            inspection.status = Inspection.Status.QUEUED
            inspection.save()

            try:
                process_single_inspection(inspection)
                messages.success(
                    request,
                    f"Component inspection for {inspection.product.product_id} completed successfully."
                )
            except Exception:
                messages.error(
                    request,
                    "Inspection processing failed. Please verify the optical capture meets dimension specifications."
                )

            return redirect(
                "inspection:inspection_detail",
                pk=inspection.pk
            )
    else:
        form = InspectionUploadForm()

    return render(
        request,
        "inspection/upload.html",
        {"form": form}
    )


@login_required
def inspection_detail(request, pk):
    """
    Displays the inspection diagnostic report.
    - Engineers see optical viewport, AI predicted class, confidence, and defect probability.
    - Supervisors additionally see the review and confirmation card/station.
    """
    inspection = get_object_or_404(
        Inspection.objects.select_related(
            "product",
            "submitted_by",
            "batch",
            "review",
            "review__reviewer"
        ),
        pk=pk
    )

    supervisor_user = is_inspection_supervisor(request.user)

    # Permission check: Engineers can view their own inspections, supervisors/admins view all
    if inspection.submitted_by != request.user and not is_supervisor(request.user):
        raise PermissionDenied

    review_form = None
    if supervisor_user and inspection.status == Inspection.Status.COMPLETED and not hasattr(inspection, "review"):
        review_form = InspectionReviewForm(
            initial={"reviewed_class": inspection.predicted_class}
        )

    return render(
        request,
        "inspection/detail.html",
        {
            "inspection": inspection,
            "is_supervisor": supervisor_user,
            "review_form": review_form,
        }
    )


# ============================================================================
# Supervisor & Engineer Operations: Inspection History & Quality Audit
# ============================================================================

@login_required
def inspection_history(request):
    """
    Inspection history and quality audit log.
    - Supervisors and Administrators see all records.
    - Supervisors have active review actions and verification filters.
    - Engineers see their own submitted inspections.
    """
    supervisor_user = is_inspection_supervisor(request.user)
    admin_user = is_administrator(request.user)

    if supervisor_user or admin_user:
        base_qs = Inspection.objects.all()
    else:
        base_qs = Inspection.objects.filter(submitted_by=request.user)

    total_count = base_qs.count()
    normal_count = base_qs.filter(predicted_class="Normal").count()
    defective_count = base_qs.filter(predicted_class="Defective").count()
    failed_count = base_qs.filter(status=Inspection.Status.FAILED).count()
    pending_review_count = base_qs.filter(status=Inspection.Status.COMPLETED, review__isnull=True).count()
    reviewed_count = base_qs.filter(review__isnull=False).count()

    prediction = request.GET.get("prediction")
    status = request.GET.get("status")
    review_status = request.GET.get("review_status")

    inspections = base_qs

    if prediction:
        inspections = inspections.filter(predicted_class=prediction)

    if status:
        inspections = inspections.filter(status=status)

    if review_status == "pending":
        inspections = inspections.filter(
            status=Inspection.Status.COMPLETED,
            review__isnull=True
        )
    elif review_status == "confirmed":
        inspections = inspections.filter(
            review__isnull=False,
            review__reviewed_class=F("predicted_class")
        )
    elif review_status == "corrected":
        inspections = inspections.filter(
            review__isnull=False
        ).exclude(
            review__reviewed_class=F("predicted_class")
        )
    elif review_status == "reviewed":
        inspections = inspections.filter(review__isnull=False)

    inspections = inspections.select_related(
        "product",
        "submitted_by",
        "review",
        "review__reviewer"
    )

    return render(
        request,
        "inspection/history.html",
        {
            "inspections": inspections,
            "selected_prediction": prediction,
            "selected_status": status,
            "selected_review_status": review_status,
            "total_count": total_count,
            "normal_count": normal_count,
            "defective_count": defective_count,
            "failed_count": failed_count,
            "pending_review_count": pending_review_count,
            "reviewed_count": reviewed_count,
            "is_supervisor": supervisor_user,
        }
    )


# ============================================================================
# Supervisor Operations: Prediction Confirmation & Correction
# ============================================================================

@login_required
def review_inspection(request, pk):
    """
    Supervisor confirms or corrects an AI prediction with an optional comment.
    Restricted to Supervisor role only.
    """
    if not is_inspection_supervisor(request.user):
        raise PermissionDenied("Inspection review and verification is restricted exclusively to the Supervisor role.")

    inspection = get_object_or_404(
        Inspection.objects.select_related("product"),
        pk=pk,
        status=Inspection.Status.COMPLETED
    )

    # Prevent duplicate reviews
    if hasattr(inspection, "review"):
        messages.warning(
            request,
            "This inspection has already received supervisor verification."
        )
        return redirect("inspection:inspection_detail", pk=inspection.pk)

    if request.method == "POST":
        form = InspectionReviewForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                inspection = Inspection.objects.select_for_update().get(
                    pk=pk,
                    status=Inspection.Status.COMPLETED
                )

                if InspectionReview.objects.filter(inspection=inspection).exists():
                    messages.warning(
                        request,
                        "This inspection has already received supervisor verification."
                    )
                    return redirect("inspection:inspection_detail", pk=inspection.pk)

                review = form.save(commit=False)
                review.inspection = inspection
                review.reviewer = request.user
                review.save()

            if review.reviewed_class == inspection.predicted_class:
                messages.success(
                    request,
                    f"Confirmed AI prediction ({inspection.predicted_class}) for Inspection #{inspection.pk}."
                )
            else:
                messages.warning(
                    request,
                    f"Corrected prediction from {inspection.predicted_class} to {review.reviewed_class} for Inspection #{inspection.pk}."
                )

            return redirect("inspection:inspection_detail", pk=inspection.pk)
    else:
        form = InspectionReviewForm(
            initial={"reviewed_class": inspection.predicted_class}
        )

    return render(
        request,
        "inspection/review.html",
        {
            "inspection": inspection,
            "form": form,
        }
    )


# ============================================================================
# Engineer Operations: Batch Ingestion & Real-Time Tracking
# ============================================================================

@engineer_required
def batch_upload(request):
    """
    Engineer uploads a small batch of images (1 to 10) and is directed to track them.
    Initializes each item in QUEUED status.
    Restricted to Engineer role.
    """
    if is_inspection_supervisor(request.user) or is_administrator(request.user):
        raise PermissionDenied("Batch image upload is restricted exclusively to the Engineer role.")

    products = Product.objects.filter(is_active=True)

    if request.method == "POST":
        product_id = request.POST.get("product")
        files = request.FILES.getlist("images")

        product = get_object_or_404(Product, pk=product_id, is_active=True)

        if not 1 <= len(files) <= 10:
            messages.error(request, "Upload between 1 and 10 images.")
            return redirect("inspection:batch_upload")

        batch = InspectionBatch.objects.create(
            product=product,
            submitted_by=request.user,
            total_files=len(files),
            status=InspectionBatch.Status.QUEUED,
        )

        for uploaded_file in files:
            try:
                validate_inspection_image(uploaded_file)
                Inspection.objects.create(
                    batch=batch,
                    product=product,
                    image=uploaded_file,
                    original_filename=uploaded_file.name,
                    submitted_by=request.user,
                    status=Inspection.Status.QUEUED,
                )
            except Exception as error:
                error_msg = "; ".join(error.messages) if hasattr(error, "messages") else str(error)
                try:
                    Inspection.objects.create(
                        batch=batch,
                        product=product,
                        image=uploaded_file,
                        original_filename=uploaded_file.name,
                        submitted_by=request.user,
                        status=Inspection.Status.FAILED,
                        failure_reason=error_msg[:1000],
                        processed_at=timezone.now(),
                    )
                except Exception:
                    Inspection.objects.create(
                        batch=batch,
                        product=product,
                        original_filename=uploaded_file.name,
                        submitted_by=request.user,
                        status=Inspection.Status.FAILED,
                        failure_reason=error_msg[:1000],
                        processed_at=timezone.now(),
                    )

        batch.completed_files = 0
        batch.failed_files = batch.inspections.filter(status=Inspection.Status.FAILED).count()
        if batch.failed_files == batch.total_files:
            batch.status = InspectionBatch.Status.FAILED
            batch.completed_at = timezone.now()
        else:
            batch.status = InspectionBatch.Status.QUEUED

        batch.save(update_fields=[
            "completed_files",
            "failed_files",
            "status",
            "completed_at",
        ])

        messages.info(
            request,
            f"Batch #{batch.pk} created with {batch.total_files} items. Ingestion queue ready."
        )

        return redirect("inspection:batch_detail", pk=batch.pk)

    return render(
        request,
        "inspection/batch_upload.html",
        {"products": products}
    )


def update_batch_status(batch):
    inspections = batch.inspections.all()

    batch.completed_files = inspections.filter(
        status=Inspection.Status.COMPLETED
    ).count()

    batch.failed_files = inspections.filter(
        status=Inspection.Status.FAILED
    ).count()

    remaining = inspections.filter(
        status__in=[Inspection.Status.QUEUED, Inspection.Status.PROCESSING]
    ).count()

    if remaining == 0:
        if batch.failed_files == batch.total_files:
            batch.status = InspectionBatch.Status.FAILED
        else:
            batch.status = InspectionBatch.Status.COMPLETED
        batch.completed_at = timezone.now()
        batch.save(update_fields=[
            "completed_files",
            "failed_files",
            "status",
            "completed_at",
        ])
    else:
        batch.status = InspectionBatch.Status.PROCESSING
        batch.save(update_fields=[
            "completed_files",
            "failed_files",
            "status",
        ])


@login_required
def batch_process_next(request, pk):
    """
    Processes the next queued inspection in the batch sequentially.
    Allows the engineer to watch items transition through QUEUED -> PROCESSING -> COMPLETED/FAILED.
    """
    batch = get_object_or_404(
        InspectionBatch.objects.prefetch_related("inspections"),
        pk=pk
    )

    supervisor_user = is_supervisor(request.user)
    if (
        batch.submitted_by != request.user
        and not supervisor_user
    ):
        return JsonResponse({"error": "Permission denied"}, status=403)

    # Find the next queued item
    inspection = batch.inspections.filter(
        status=Inspection.Status.QUEUED
    ).order_by("id").first()

    if inspection:
        inspection.status = Inspection.Status.PROCESSING
        inspection.save(update_fields=["status"])

        batch.status = InspectionBatch.Status.PROCESSING
        batch.save(update_fields=["status"])

        try:
            process_single_inspection(inspection)
        except Exception:
            pass

        inspection.refresh_from_db()

    # Recompute batch summary statistics
    all_inspections = batch.inspections.all()
    completed_count = all_inspections.filter(status=Inspection.Status.COMPLETED).count()
    failed_count = all_inspections.filter(status=Inspection.Status.FAILED).count()
    remaining_count = all_inspections.filter(status=Inspection.Status.QUEUED).count()
    processing_count = all_inspections.filter(status=Inspection.Status.PROCESSING).count()
    normal_count = all_inspections.filter(predicted_class="Normal").count()
    defective_count = all_inspections.filter(predicted_class="Defective").count()

    batch.completed_files = completed_count
    batch.failed_files = failed_count

    is_finished = (remaining_count == 0 and processing_count == 0)
    if is_finished:
        if failed_count == batch.total_files:
            batch.status = InspectionBatch.Status.FAILED
        else:
            batch.status = InspectionBatch.Status.COMPLETED
        batch.completed_at = timezone.now()
        batch.save(update_fields=["completed_files", "failed_files", "status", "completed_at"])
    else:
        batch.save(update_fields=["completed_files", "failed_files"])

    response_data = {
        "success": True,
        "has_more": not is_finished,
        "finished": is_finished,
        "batch": {
            "id": batch.id,
            "status": batch.status,
            "status_display": batch.get_status_display(),
            "total": batch.total_files,
            "completed": completed_count,
            "failed": failed_count,
            "remaining": remaining_count,
            "normal": normal_count,
            "defective": defective_count,
        }
    }

    if inspection:
        response_data["item"] = {
            "id": inspection.id,
            "status": inspection.status,
            "status_display": inspection.get_status_display(),
            "predicted_class": inspection.predicted_class,
            "confidence": round(inspection.confidence, 4) if inspection.confidence is not None else None,
            "defect_probability": round(inspection.defect_probability, 4) if inspection.defect_probability is not None else None,
            "failure_reason": inspection.failure_reason,
        }

    return JsonResponse(response_data)


@login_required
def batch_status(request, pk):
    """
    Returns JSON status snapshot of a batch and all its items.
    """
    batch = get_object_or_404(
        InspectionBatch.objects.prefetch_related("inspections"),
        pk=pk
    )

    supervisor_user = is_supervisor(request.user)
    if (
        batch.submitted_by != request.user
        and not supervisor_user
    ):
        return JsonResponse({"error": "Permission denied"}, status=403)

    all_inspections = batch.inspections.all()
    items = []
    for item in all_inspections:
        items.append({
            "id": item.id,
            "filename": item.original_filename or (item.image.name if item.image else ""),
            "status": item.status,
            "status_display": item.get_status_display(),
            "predicted_class": item.predicted_class,
            "confidence": round(item.confidence, 4) if item.confidence is not None else None,
            "defect_probability": round(item.defect_probability, 4) if item.defect_probability is not None else None,
            "failure_reason": item.failure_reason,
        })

    return JsonResponse({
        "batch": {
            "id": batch.id,
            "status": batch.status,
            "status_display": batch.get_status_display(),
            "total": batch.total_files,
            "completed": batch.completed_files,
            "failed": batch.failed_files,
            "normal": all_inspections.filter(predicted_class="Normal").count(),
            "defective": all_inspections.filter(predicted_class="Defective").count(),
        },
        "items": items,
    })


@login_required
def batch_detail(request, pk):
    batch = get_object_or_404(
        InspectionBatch.objects.prefetch_related("inspections"),
        pk=pk
    )

    supervisor_user = is_supervisor(request.user)
    if (
        batch.submitted_by != request.user
        and not supervisor_user
    ):
        raise PermissionDenied

    inspections = batch.inspections.all()
    normal_count = inspections.filter(predicted_class="Normal").count()
    defective_count = inspections.filter(predicted_class="Defective").count()
    has_queued = inspections.filter(
        status__in=[Inspection.Status.QUEUED, Inspection.Status.PROCESSING]
    ).exists()

    return render(
        request,
        "inspection/batch_detail.html",
        {
            "batch": batch,
            "normal_count": normal_count,
            "defective_count": defective_count,
            "has_queued": has_queued,
            "is_supervisor": supervisor_user,
        }
    )


# ============================================================================
# Supervisor Operations: Model Benchmark Evaluation
# ============================================================================

@login_required
def model_evaluation(request):
    """
    Runs model benchmark evaluation across all reference samples.
    Available to Supervisor role only.
    """
    if not is_inspection_supervisor(request.user):
        raise PermissionDenied("Model evaluation is restricted exclusively to the Supervisor role.")

    evaluation = evaluate_model()

    return render(
        request,
        "inspection/evaluation.html",
        {
            "evaluation": evaluation,
            "is_supervisor": True,
            "is_admin": False,
        }
    )
