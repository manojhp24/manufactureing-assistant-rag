from django import forms
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError

ROLE_CHOICES = [
    ("Engineer", "Engineer — Field Maintenance AI & Visual Quality Inspections"),
    ("Supervisor", "Supervisor — Shift Auditing, Verification Sign-Off & Benchmarks"),
    ("Administrator", "Administrator — Machinery Fleet, PDF Manuals & User Management"),
]


class UserCreateForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial="Engineer",
        widget=forms.RadioSelect,
        help_text="Select primary operational clearance role for this operator"
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Enter secure initial password (min 8 characters)",
            "autocomplete": "new-password",
        }),
        min_length=8,
        help_text="Temporary credential for station access (min 8 characters)"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Re-enter password to confirm",
            "autocomplete": "new-password",
        }),
        min_length=8,
    )

    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., arun_engineer",
                "autocomplete": "off",
            }),
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., arun.eng@mma-industrial.com",
            }),
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "First Name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Last Name",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "style": "width: 18px; height: 18px; cursor: pointer;",
            }),
        }

    def clean_username(self):
        username = self.cleaned_data.get("username", "").strip()
        if not username:
            raise ValidationError("Username is required.")
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError(f"A user with username '{username}' already exists.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        pw = cleaned_data.get("password")
        cpw = cleaned_data.get("confirm_password")
        if pw and cpw and pw != cpw:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        role = self.cleaned_data.get("role")
        if role == "Administrator":
            user.is_staff = True
        else:
            user.is_staff = False

        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name=role)
            user.groups.clear()
            user.groups.add(group)
        return user


class UserEditForm(forms.ModelForm):
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        widget=forms.RadioSelect,
        help_text="Select primary operational clearance role"
    )
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={
            "class": "form-control",
            "placeholder": "Leave blank to keep existing password",
            "autocomplete": "new-password",
        }),
        min_length=8,
        help_text="Optional: enter a new password (min 8 characters) to reset credentials"
    )

    class Meta:
        model = User
        fields = ["email", "first_name", "last_name", "is_active"]
        widgets = {
            "email": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "e.g., operator@mma-industrial.com",
            }),
            "first_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "First Name",
            }),
            "last_name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Last Name",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
                "style": "width: 18px; height: 18px; cursor: pointer;",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            user_groups = list(self.instance.groups.values_list("name", flat=True))
            if "Administrator" in user_groups or self.instance.is_superuser:
                self.fields["role"].initial = "Administrator"
            elif "Supervisor" in user_groups:
                self.fields["role"].initial = "Supervisor"
            elif "Engineer" in user_groups:
                self.fields["role"].initial = "Engineer"
            else:
                self.fields["role"].initial = "Engineer"

    def save(self, commit=True):
        user = super().save(commit=False)
        new_pw = self.cleaned_data.get("new_password")
        if new_pw:
            user.set_password(new_pw)

        role = self.cleaned_data.get("role")
        if role == "Administrator":
            user.is_staff = True
        else:
            if not user.is_superuser:
                user.is_staff = False

        if commit:
            user.save()
            group, _ = Group.objects.get_or_create(name=role)
            all_role_groups = Group.objects.filter(name__in=["Administrator", "Supervisor", "Engineer"])
            user.groups.remove(*all_role_groups)
            user.groups.add(group)
        return user

