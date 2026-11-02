from django import forms
from .models import Manual


class ManualUploadForm(forms.ModelForm):

    class Meta:
        model = Manual
        fields = [
            "machine",
            "document_id",
            "title",
            "revision",
            "pdf_file",
        ]

        widgets = {
            "machine": forms.Select(attrs={"class": "form-control"}),
            "document_id": forms.TextInput(attrs={"class": "form-control"}),
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "revision": forms.TextInput(attrs={"class": "form-control"}),
            "pdf_file": forms.FileInput(attrs={"class": "form-control"}),
        }

    def clean_pdf_file(self):
        file = self.cleaned_data["pdf_file"]

        if not file.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF files are allowed.")

        if file.size > 20 * 1024 * 1024:
            raise forms.ValidationError("Maximum PDF size is 20 MB.")

        return file