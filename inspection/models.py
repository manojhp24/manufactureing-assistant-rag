
from django.db import models
from django.contrib.auth.models import User


class Product(models.Model):
    product_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["product_id"]

    def __str__(self):
        return f"{self.product_id} - {self.name}"


class InspectionBatch(models.Model):

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="batches"
    )

    submitted_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="inspection_batches"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED
    )

    total_files = models.PositiveIntegerField(default=0)
    completed_files = models.PositiveIntegerField(default=0)
    failed_files = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Batch #{self.pk} - {self.status}"


class Inspection(models.Model):

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    class Prediction(models.TextChoices):
        NORMAL = "Normal", "Normal"
        DEFECTIVE = "Defective", "Defective"

    batch = models.ForeignKey(
        InspectionBatch,
        on_delete=models.CASCADE,
        related_name="inspections",
        null=True,
        blank=True
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="inspections"
    )

    image = models.ImageField(
        upload_to="inspections/%Y/%m/"
    )
    original_filename = models.CharField(max_length=255, blank=True)

    submitted_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="inspections"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.QUEUED
    )

    # Original classifier output
    predicted_class = models.CharField(
        max_length=20,
        choices=Prediction.choices,
        null=True,
        blank=True
    )

    confidence = models.FloatField(null=True, blank=True)
    defect_probability = models.FloatField(null=True, blank=True)
    model_version = models.CharField(max_length=100, blank=True)

    failure_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["predicted_class"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Inspection #{self.pk} - {self.status}"


class InspectionReview(models.Model):

    inspection = models.OneToOneField(
        Inspection,
        on_delete=models.CASCADE,
        related_name="review"
    )

    reviewed_class = models.CharField(
        max_length=20,
        choices=Inspection.Prediction.choices
    )

    reviewer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="inspection_reviews"
    )

    comment = models.TextField(blank=True)

    reviewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-reviewed_at"]

    def __str__(self):
        return f"Review for Inspection #{self.inspection_id}"
