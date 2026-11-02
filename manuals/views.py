from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import render, redirect

from accounts.permissions import administrator_required
from machines.models import Machine
from .forms import ManualUploadForm
from .models import Manual
from .services import index_manual


@login_required
@administrator_required
def upload_manual(request):

    if request.method == "POST":
        form = ManualUploadForm(request.POST, request.FILES)

        if form.is_valid():
            manual = form.save(commit=False)
            manual.save()

            try:
                result = index_manual(manual)
                pages = result.get("total_pages", manual.total_pages)
                chunks = result.get("total_chunks", manual.total_chunks)

                messages.success(
                    request,
                    f"Manual '{manual.title}' (Doc ID: {manual.document_id}) uploaded and indexed into ChromaDB ({pages} pages, {chunks} semantic chunks)."
                )

            except Exception as error:
                messages.warning(
                    request,
                    f"Manual '{manual.title}' saved to database, but vector indexing encountered an issue: {error}. You can re-index it from the manual list."
                )

            return redirect("manual_list")

    else:
        initial = {}
        machine_id = request.GET.get("machine")
        if machine_id:
            initial["machine"] = machine_id
        form = ManualUploadForm(initial=initial)

    recent_manuals = Manual.objects.select_related("machine").order_by("-uploaded_at")[:4]
    active_machines_count = Machine.objects.filter(is_active=True).count()
    machines = Machine.objects.filter(is_active=True).order_by("name")

    return render(
        request,
        "manuals/upload.html",
        {
            "form": form,
            "recent_manuals": recent_manuals,
            "active_machines_count": active_machines_count,
            "machines": machines,
        }
    )


@login_required
@administrator_required
def manual_list(request):

    machine_id = request.GET.get("machine")
    status_filter = request.GET.get("status")
    search_query = request.GET.get("q", "").strip()

    queryset = Manual.objects.select_related("machine").order_by("-uploaded_at")

    selected_machine = None
    if machine_id:
        queryset = queryset.filter(machine_id=machine_id)
        selected_machine = Machine.objects.filter(id=machine_id).first()

    if status_filter in ["indexed", "pending", "failed"]:
        queryset = queryset.filter(indexing_status=status_filter)

    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(document_id__icontains=search_query) |
            Q(revision__icontains=search_query) |
            Q(machine__name__icontains=search_query) |
            Q(machine__model_number__icontains=search_query)
        )

    # Aggregates across the knowledge base
    all_manuals = Manual.objects.all()
    total_count = all_manuals.count()
    indexed_count = all_manuals.filter(indexing_status="indexed").count()
    pending_count = all_manuals.filter(indexing_status="pending").count()
    failed_count = all_manuals.filter(indexing_status="failed").count()
    total_pages_sum = all_manuals.aggregate(s=Sum("total_pages"))["s"] or 0
    total_chunks_sum = all_manuals.aggregate(s=Sum("total_chunks"))["s"] or 0

    machines = Machine.objects.filter(is_active=True).order_by("name")

    return render(
        request,
        "manuals/list.html",
        {
            "manuals": queryset,
            "total_count": total_count,
            "indexed_count": indexed_count,
            "pending_count": pending_count,
            "failed_count": failed_count,
            "total_pages_sum": total_pages_sum,
            "total_chunks_sum": total_chunks_sum,
            "machines": machines,
            "selected_machine": selected_machine,
            "machine_id": machine_id,
            "status_filter": status_filter,
            "search_query": search_query,
        }
    )
