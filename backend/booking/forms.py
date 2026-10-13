from django import forms

from .db import laboratories

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
