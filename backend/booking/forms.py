from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils import timezone

from accounts.models import User

from .db import laboratories, managed_laboratories

EQUIPMENT_STATUSES = [(value, value.title()) for value in ("available", "maintenance", "retired")]


class EquipmentFilter(forms.Form):
    q = forms.CharField(label="Name or asset tag", max_length=100, required=False)
    laboratory = forms.ChoiceField(required=False)
    category = forms.CharField(max_length=80, required=False)
    status = forms.ChoiceField(choices=[("", "All statuses")] + EQUIPMENT_STATUSES, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["laboratory"].choices = [("", "All laboratories")] + [(lab["id"], lab["code"]) for lab in laboratories()]


class LaboratoryFilter(forms.Form):
    q = forms.CharField(label="Code or name", max_length=100, required=False)
    location = forms.CharField(max_length=160, required=False)


RESERVATION_STATUSES = [(value, value.title()) for value in ("pending", "approved", "rejected", "cancelled")]


class ReservationForm(forms.Form):
    purpose = forms.CharField(max_length=500, widget=forms.Textarea(attrs={"rows": 3}))
    starts_at = forms.DateTimeField(label="Start", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    ends_at = forms.DateTimeField(label="End", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))

    def clean(self):
        data = super().clean()
        start, end = data.get("starts_at"), data.get("ends_at")
        if start and start <= timezone.now():
            self.add_error("starts_at", "Choose a future start time.")
        if start and end and end <= start:
            self.add_error("ends_at", "End must be after start.")
        return data


class ReservationFilter(forms.Form):
    status = forms.ChoiceField(required=False, choices=[("", "All statuses")] + RESERVATION_STATUSES)
    q = forms.CharField(label="Equipment name", max_length=100, required=False)


class EquipmentForm(forms.Form):
    laboratory_id = forms.TypedChoiceField(label="Laboratory", coerce=int)
    asset_tag = forms.CharField(max_length=40)
    name = forms.CharField(max_length=120)
    category = forms.CharField(max_length=80)
    description = forms.CharField(required=False, max_length=5000, widget=forms.Textarea(attrs={"rows": 3}))
    status = forms.ChoiceField(choices=EQUIPMENT_STATUSES)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["laboratory_id"].choices = [(lab["id"], lab["code"]) for lab in managed_laboratories(user)]


class LaboratoryForm(forms.Form):
    code = forms.CharField(max_length=24)
    name = forms.CharField(max_length=120)
    location = forms.CharField(max_length=160)
    managers = forms.ModelMultipleChoiceField(queryset=User.objects.none(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["managers"].queryset = User.objects.filter(role="manager", is_active=True).order_by("username")
        self.fields["managers"].help_text = "Select active laboratory managers. Hold Ctrl or Command to select more than one."


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "role", "is_active"]

    def clean_email(self):
        email = self.cleaned_data["email"]
        if not email:
            raise forms.ValidationError("Email is required for password reset.")
        return email


class UserCreateForm(UserCreationForm):
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email", "role"]
