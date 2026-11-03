from Model.inference import predict
from .validators import validate_inspection_image


def run_inspection(image_file):
    print("DEBUG: Starting inspection")
    print("DEBUG: Image name:", image_file.name)
    print("DEBUG: Image path:", image_file.path)

    validate_inspection_image(image_file)
    print("DEBUG: Image validation successful")

    result = predict(image_file.path)
    print("DEBUG: Classifier result:", result)

    return {
        "predicted_class": result["predicted_class"],
        "confidence": float(result["confidence"]),
        "defect_probability": float(result["defect_probability"]),
        "model_version": result["model_version"],
    }

from django.utils import timezone
from django.db import transaction

from .models import Inspection


def process_single_inspection(inspection):

    try:
        inspection.status = Inspection.Status.PROCESSING
        inspection.save(update_fields=["status"])

        result = run_inspection(inspection.image)

        with transaction.atomic():
            inspection.predicted_class = result["predicted_class"]
            inspection.confidence = result["confidence"]
            inspection.defect_probability = result["defect_probability"]
            inspection.model_version = result["model_version"]

            inspection.status = Inspection.Status.COMPLETED
            inspection.processed_at = timezone.now()

            inspection.save()

        return inspection

    except Exception as error:
        print("INSPECTION ERROR:", repr(error))

        inspection.status = Inspection.Status.FAILED
        inspection.failure_reason = str(error)[:1000]
        inspection.processed_at = timezone.now()

        inspection.save(update_fields=[
            "status",
            "failure_reason",
            "processed_at",
        ])

        raise