from django.db import models
from machines.models import Machine


class Manual(models.Model):

    class IndexingStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        INDEXED = "indexed", "Indexed"
        FAILED = "failed", "Failed"

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="manuals"
    )

    document_id = models.CharField(max_length=100, unique=True)

    title = models.CharField(max_length=200)

    revision = models.CharField(max_length=50)

    pdf_file = models.FileField(
        upload_to="manuals/%Y/%m/"
    )

    indexing_status = models.CharField(
        max_length=20,
        choices=IndexingStatus.choices,
        default=IndexingStatus.PENDING
    )

    total_pages = models.PositiveIntegerField(default=0)

    total_chunks = models.PositiveIntegerField(default=0)

    uploaded_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-uploaded_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["machine", "document_id", "revision"],
                name="unique_machine_manual_revision"
            )
        ]

    def __str__(self):
        return f"{self.title} - Rev {self.revision}"