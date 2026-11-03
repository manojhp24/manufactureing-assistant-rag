from PIL import Image, UnidentifiedImageError
from django.core.exceptions import ValidationError

MAX_FILE_SIZE = 5 * 1024 * 1024
MIN_DIMENSION = 64
MAX_DIMENSION = 4096

ALLOWED_FORMATS = {"JPEG", "PNG"}


def validate_inspection_image(uploaded_file):

    if not uploaded_file:
        raise ValidationError("Please select an image.")

    if uploaded_file.size == 0:
        raise ValidationError("Empty files are not allowed.")

    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValidationError("Image size must not exceed 5 MB.")

    try:
        uploaded_file.seek(0)

        with Image.open(uploaded_file) as image:
            if image.format not in ALLOWED_FORMATS:
                raise ValidationError("Only JPEG and PNG images are allowed.")

            width, height = image.size

            if not (
                MIN_DIMENSION <= width <= MAX_DIMENSION
                and MIN_DIMENSION <= height <= MAX_DIMENSION
            ):
                raise ValidationError(
                    "Image dimensions must be between 64 and 4096 pixels."
                )

            image.verify()

        uploaded_file.seek(0)

    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError("The uploaded file is not a valid image.")

    finally:
        uploaded_file.seek(0)