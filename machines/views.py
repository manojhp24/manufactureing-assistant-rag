from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from accounts.permissions import (
    administrator_required,
    supervisor_required,
    engineer_required,
)
from .models import Machine
from .forms import MachineForm


@engineer_required
def machine_list(request):
    """
    List industrial shopfloor machinery fleet.
    Accessible to Engineers, Supervisors, and Administrators.
    Optimized with manuals count annotation to eliminate N+1 SQL queries.
    Supports search query and status filtering.
    """
    search_query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    queryset = Machine.objects.annotate(manuals_count=Count("manuals"))

    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query)
            | Q(model_number__icontains=search_query)
            | Q(description__icontains=search_query)
        )

    if status_filter == "active":
        queryset = queryset.filter(is_active=True)
    elif status_filter == "inactive":
        queryset = queryset.filter(is_active=False)

    machines = queryset.all()

    # Fleet statistics for badges / KPIs
    total_count = Machine.objects.count()
    active_count = Machine.objects.filter(is_active=True).count()
    inactive_count = total_count - active_count

    return render(
        request,
        "machines/machine_list.html",
        {
            "machines": machines,
            "search_query": search_query,
            "status_filter": status_filter,
            "total_count": total_count,
            "active_count": active_count,
            "inactive_count": inactive_count,
        },
    )


@administrator_required
def machine_create(request):
    """
    Register new industrial machinery in the plant database.
    Restricted to System Administrators.
    """
    if request.method == "POST":
        form = MachineForm(request.POST)
        if form.is_valid():
            machine = form.save()
            messages.success(
                request,
                f"Machine '{machine.name}' ({machine.model_number}) registered successfully."
            )
            return redirect("machine_list")
    else:
        form = MachineForm()

    recent_machines = Machine.objects.order_by("-created_at")[:5]

    return render(
        request,
        "machines/machine_form.html",
        {
            "form": form,
            "title": "Register Machine",
            "machine": None,
            "recent_machines": recent_machines,
        },
    )


@supervisor_required
def machine_edit(request, pk):
    """
    Update equipment specifications or status.
    Accessible to Supervisors and Administrators.
    """
    machine = get_object_or_404(Machine, pk=pk)

    if request.method == "POST":
        form = MachineForm(request.POST, instance=machine)
        if form.is_valid():
            machine = form.save()
            messages.success(
                request,
                f"Machine '{machine.name}' ({machine.model_number}) updated successfully."
            )
            return redirect("machine_list")
    else:
        form = MachineForm(instance=machine)

    recent_machines = Machine.objects.exclude(pk=machine.pk).order_by("-created_at")[:5]

    return render(
        request,
        "machines/machine_form.html",
        {
            "form": form,
            "title": "Edit Machine",
            "machine": machine,
            "recent_machines": recent_machines,
        },
    )


@require_POST
@administrator_required
def machine_toggle_status(request, pk):
    """
    Quick-toggle active/decommissioned operational status.
    Restricted to Administrators.
    """
    machine = get_object_or_404(Machine, pk=pk)
    machine.is_active = not machine.is_active
    machine.save(update_fields=["is_active", "updated_at"])

    status_str = "Operational" if machine.is_active else "Decommissioned"
    messages.success(
        request,
        f"Machine '{machine.name}' status set to {status_str}."
    )
    return redirect("machine_list")
