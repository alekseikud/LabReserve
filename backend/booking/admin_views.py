from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from accounts.models import User
from accounts.permissions import roles_required
from .db import laboratories, one, query
from .forms import LaboratoryForm, UserCreateForm, UserEditForm
from .views import page_context


@never_cache
@roles_required("admin")
@require_GET
def laboratory_manage(request):
    return render(request, "booking/laboratory_manage.html", {"labs": laboratories()})


@never_cache
@roles_required("admin")
@require_http_methods(["GET", "POST"])
def laboratory_edit(request, pk=None):
    initial = one("SELECT * FROM inventory_laboratory WHERE id = %s", [pk]) if pk else {}
    if pk:
        initial["managers"] = [row["user_id"] for row in query("SELECT user_id FROM inventory_laboratory_managers WHERE laboratory_id = %s", [pk])]
    form = LaboratoryForm(request.POST if request.method == "POST" else None, initial=initial)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            with transaction.atomic():
                values = [data["code"], data["name"], data["location"]]
                if pk:
                    lab = one("UPDATE inventory_laboratory SET code = %s, name = %s, location = %s WHERE id = %s RETURNING id", values + [pk])
                else:
                    lab = one("INSERT INTO inventory_laboratory (code, name, location) VALUES (%s, %s, %s) RETURNING id", values)
                query("DELETE FROM inventory_laboratory_managers WHERE laboratory_id = %s", [lab["id"]])
                for manager in data["managers"]:
                    query("INSERT INTO inventory_laboratory_managers (laboratory_id, user_id) VALUES (%s, %s)", [lab["id"], manager.pk])
        except IntegrityError:
            form.add_error("code", "That laboratory code is already used.")
        else:
            return redirect("laboratory_manage")
    return render(request, "booking/form.html", {"form": form, "heading": "Edit laboratory" if pk else "Add laboratory"})


@never_cache
@roles_required("admin")
@require_GET
def user_manage(request):
    return render(request, "booking/user_manage.html", page_context(request, User.objects.order_by("username")))


@never_cache
@roles_required("admin")
@require_http_methods(["GET", "POST"])
def user_edit(request, pk=None):
    # Serialise administrator edits so two requests cannot both remove the last admin.
    with transaction.atomic():
        if request.method == "POST":
            list(User.objects.select_for_update().filter(role="admin", is_active=True).order_by("pk"))
        user = get_object_or_404(User, pk=pk) if pk else None
        form_class = UserEditForm if pk else UserCreateForm
        form = form_class(request.POST if request.method == "POST" else None, instance=user)
        if request.method == "POST" and form.is_valid():
            data = form.cleaned_data
            if pk == request.user.pk and (data["role"] != "admin" or not data["is_active"]):
                form.add_error(None, "You cannot remove your own administrator access.")
            elif pk and (data["role"] != "admin" or not data["is_active"]) and not User.objects.filter(role="admin", is_active=True).exclude(pk=pk).exists():
                form.add_error(None, "At least one active administrator must remain.")
            else:
                try:
                    with transaction.atomic():
                        saved = form.save()
                        if saved.role != "manager" or not saved.is_active:
                            query("DELETE FROM inventory_laboratory_managers WHERE user_id = %s", [saved.pk])
                except IntegrityError:
                    form.add_error(None, "That username or email is already used.")
                else:
                    return redirect("user_manage")
    return render(request, "booking/form.html", {"form": form, "heading": "Edit user" if pk else "Add user"})
