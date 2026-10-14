from django import forms
from django.utils import timezone

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
