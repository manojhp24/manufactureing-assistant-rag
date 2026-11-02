
from django import forms
from machines.models import Machine


class QuestionForm(forms.Form):
    machine = forms.ModelChoiceField(
        queryset=Machine.objects.filter(is_active=True),
        empty_label="Select a machine",
        widget=forms.Select(attrs={
            "class": "form-control",
        })
    )

    question = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 4,
            "placeholder": "Describe your machine issue or maintenance question...",
        }),
        max_length=2000,
    )
