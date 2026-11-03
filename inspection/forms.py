from django import forms
from .models import Inspection, Product, InspectionReview
from .validators import validate_inspection_image


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = ["product_id", "name", "description", "is_active"]
        widgets = {
            "product_id": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., P-PLATE01",
                "style": "font-family: var(--font-mono); text-transform: uppercase;"
            }),
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., Demonstration metal plate"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Component specifications, alloy composition, surface finish tolerances..."
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "style": "width: 18px; height: 18px; cursor: pointer;"
            }),
        }

    def clean_product_id(self):
        pid = self.cleaned_data.get("product_id", "").strip().upper()
        if not pid:
            raise forms.ValidationError("Product ID is required.")
        return pid


class InspectionUploadForm(forms.ModelForm):

    class Meta:
        model = Inspection
        fields = ["product", "image"]

        widgets = {
            "product": forms.Select(attrs={
                "class": "form-control"
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "form-control",
                "accept": ".jpg,.jpeg,.png"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["product"].queryset = Product.objects.filter(
            is_active=True
        )

    def clean_image(self):
        image = self.cleaned_data.get("image")
        validate_inspection_image(image)
        return image


class InspectionReviewForm(forms.ModelForm):

    class Meta:
        model = InspectionReview
        fields = ["reviewed_class", "comment"]

        widgets = {
            "reviewed_class": forms.Select(
                attrs={"class": "form-control"}
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Add optional review comments, observations, or corrective actions..."
                }
            ),
        }
