from django import forms
from .models import Machine


class MachineForm(forms.ModelForm):
    """
    Form for registering and updating industrial plant machinery.
    Normalizes model numbers and cleans input text.
    """
    class Meta:
        model = Machine
        fields = ["name", "model_number", "description", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. CNC 5-Axis Milling Center",
                "autofocus": True,
            }),
            "model_number": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Example: M-HP200",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 4,
                "placeholder": "Operating cell, electrical load, cooling specifications, preventive maintenance schedules...",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }
        help_texts = {
            "name": "Plant floor name or equipment station label.",
            "model_number": "Unique manufacturer model number used for machine isolation in RAG queries.",
            "is_active": "Active in Production (Enabled for Maintenance AI Queries)",
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Machine name cannot be blank.")
        return name

    def clean_model_number(self):
        model_number = self.cleaned_data.get("model_number", "").strip().upper()
        if not model_number:
            raise forms.ValidationError("Model number is required.")

        # Check unique constraint with case-insensitivity
        query = Machine.objects.filter(model_number__iexact=model_number)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise forms.ValidationError(
                f"A machine with model number '{model_number}' is already registered in the fleet."
            )

        return model_number

    def clean_description(self):
        description = self.cleaned_data.get("description", "")
        return description.strip() if description else ""

        help_texts = {
            "name": "Plant floor name or equipment station label.",
            "model_number": "Unique manufacturer model number used for machine isolation in RAG queries.",
            "is_active": "Active in Production (Enabled for Maintenance AI Queries)",
        }

    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        if not name:
            raise forms.ValidationError("Machine name cannot be blank.")
        return name

    def clean_model_number(self):
        model_number = self.cleaned_data.get("model_number", "").strip().upper()
        if not model_number:
            raise forms.ValidationError("Model number is required.")

        # Check unique constraint with case-insensitivity
        query = Machine.objects.filter(model_number__iexact=model_number)
        if self.instance and self.instance.pk:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise forms.ValidationError(
                f"A machine with model number '{model_number}' is already registered in the fleet."
            )

        return model_number

    def clean_description(self):
        description = self.cleaned_data.get("description", "")
        return description.strip() if description else ""