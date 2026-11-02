from django import forms
from machines.models import Machine
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
            "machine": forms.Select(attrs={
                "class": "form-control",
                "id": "id_machine",
            }),
            "document_id": forms.TextInput(attrs={
                "class": "form-control",
                "id": "id_document_id",
                "placeholder": "e.g. MAN-DMG-5000-ELEC",
                "style": "font-family: var(--font-mono); text-transform: uppercase;",
            }),
            "title": forms.TextInput(attrs={
                "class": "form-control",
                "id": "id_title",
                "placeholder": "e.g. Maintenance & Troubleshooting Guide - Spindle Drive",
            }),
            "revision": forms.TextInput(attrs={
                "class": "form-control",
                "id": "id_revision",
                "placeholder": "e.g. 1.0",
                "style": "font-family: var(--font-mono);",
            }),
            "pdf_file": forms.FileInput(attrs={
                "class": "form-control",
                "id": "id_pdf_file",
                "accept": "application/pdf",
                "style": "display: none;",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["machine"].queryset = Machine.objects.filter(is_active=True).order_by("name")
        self.fields["machine"].empty_label = "— Select Target Machinery Fleet —"
        if not self.initial.get("revision"):
            self.fields["revision"].initial = "1.0"

    def clean_document_id(self):
        doc_id = self.cleaned_data.get("document_id", "").strip().upper()
        if not doc_id:
            raise forms.ValidationError("Document identifier is required.")
        return doc_id

    def clean_revision(self):
        rev = self.cleaned_data.get("revision", "").strip().upper()
        if not rev:
            raise forms.ValidationError("Revision code is required.")
        return rev

    def clean_pdf_file(self):
        file = self.cleaned_data.get("pdf_file")
        if not file:
            raise forms.ValidationError("Please select a PDF manual file to upload.")

        if not file.name.lower().endswith(".pdf"):
            raise forms.ValidationError("Only PDF technical manual files are supported.")

        if file.size > 20 * 1024 * 1024:
            raise forms.ValidationError("File size exceeds 20 MB limit. Please optimize or split the document.")

        return file
