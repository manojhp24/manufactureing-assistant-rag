
import csv
from pathlib import Path

from django.conf import settings
from Model.inference import predict


SAMPLES_DIR = Path(settings.BASE_DIR) / "Samples"
LABELS_FILE = SAMPLES_DIR / "labels.csv"

CLASS_ORDER = ["Normal", "Defective"]


def evaluate_model():
    results = []
    failed = []

    with open(LABELS_FILE, newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            image_path = SAMPLES_DIR / row["relative_path"]
            actual = row["label"]

            try:
                if not image_path.is_file():
                    raise FileNotFoundError(
                        f"Image not found: {image_path}"
                    )

                output = predict(str(image_path))
                predicted = output["predicted_class"]

                if predicted not in CLASS_ORDER:
                    raise ValueError(
                        f"Unexpected prediction: {predicted}"
                    )

                results.append({
                    "image_id": row["image_id"],
                    "actual": actual,
                    "predicted": predicted,
                })

            except Exception as error:
                failed.append({
                    "image_id": row["image_id"],
                    "reason": str(error),
                })

    tp = sum(
        r["actual"] == "Defective"
        and r["predicted"] == "Defective"
        for r in results
    )

    tn = sum(
        r["actual"] == "Normal"
        and r["predicted"] == "Normal"
        for r in results
    )

    fp = sum(
        r["actual"] == "Normal"
        and r["predicted"] == "Defective"
        for r in results
    )

    fn = sum(
        r["actual"] == "Defective"
        and r["predicted"] == "Normal"
        for r in results
    )

    total = len(results)

    accuracy = (tp + tn) / total if total else 0
    precision = tp / (tp + fp) if (tp + fp) else 0
    recall = tp / (tp + fn) if (tp + fn) else 0

    return {
        "total_samples": 60,
        "evaluated": total,
        "failed": len(failed),
        "confusion_matrix": {
            "Normal": {
                "Normal": tn,
                "Defective": fp,
            },
            "Defective": {
                "Normal": fn,
                "Defective": tp,
            },
        },
        "accuracy": accuracy,
        "defect_precision": precision,
        "defect_recall": recall,
        "failed_images": failed,
    }
