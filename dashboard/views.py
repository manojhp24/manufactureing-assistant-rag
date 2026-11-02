from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from accounts.permissions import (
    administrator_required,
    engineer_required,
    supervisor_required,
    is_administrator,
    is_supervisor,
    is_engineer,
)
from machines.models import Machine
from manuals.models import Manual
from assistant.models import QuestionAnswer


@login_required
def dashboard_home(request):
    """
    Role-aware traffic router. Directs user to their dedicated dashboard
    based on verified group permissions or superuser status.
    """
    user = request.user
    if is_administrator(user):
        return redirect("admin_dashboard")
    if is_supervisor(user):
        return redirect("supervisor_dashboard")
    if is_engineer(user):
        return redirect("engineer_dashboard")

    # Fallback for authenticated users without an explicit role
    return redirect("engineer_dashboard")


@administrator_required
def admin_dashboard(request):
    """
    Administrator Operations Console.
    Supplies fleet counts, PDF ingestion pipeline health, and system-wide activity metrics.
    """
    total_machines = Machine.objects.count()
    total_manuals = Manual.objects.count()
    indexed_manuals = Manual.objects.filter(
        indexing_status=Manual.IndexingStatus.INDEXED
    ).count()
    failed_manuals = Manual.objects.filter(
        indexing_status=Manual.IndexingStatus.FAILED
    ).count()

    recent_uploads = (
        Manual.objects.select_related("machine")
        .order_by("-uploaded_at")[:5]
    )

    # Activity stream combining recent manual uploads and assistant inquiries
    recent_activity = []
    for manual in recent_uploads:
        recent_activity.append({
            "description": f"Manual Ingested: {manual.title} ({manual.machine.model_number})",
            "timestamp": manual.uploaded_at,
            "user": "System Ingestion",
        })

    recent_inquiries = (
        QuestionAnswer.objects.select_related("machine", "engineer")
        .order_by("-created_at")[:5]
    )
    for q in recent_inquiries:
        recent_activity.append({
            "description": f"Diagnosis Inquiry for {q.machine.name} ({q.machine.model_number})",
            "timestamp": q.created_at,
            "user": q.engineer.get_full_name() or q.engineer.username,
        })

    recent_activity.sort(key=lambda item: item["timestamp"], reverse=True)
    recent_activity = recent_activity[:8]

    context = {
        "total_machines": total_machines,
        "total_manuals": total_manuals,
        "indexed_manuals": indexed_manuals,
        "failed_manuals": failed_manuals,
        "recent_uploads": recent_uploads,
        "recent_activity": recent_activity,
    }
    return render(request, "dashboard/admin_dashboard.html", context)


@engineer_required
def engineer_dashboard(request):
    """
    Maintenance Engineering Field Console.
    Supplies active equipment fleet with ingested manuals, recent personal queries,
    and field terminal KPIs.
    """
    active_machines_count = Machine.objects.filter(is_active=True).count()
    machines = Machine.objects.filter(is_active=True).prefetch_related("manuals")

    user_queries = QuestionAnswer.objects.filter(engineer=request.user)
    my_questions_count = user_queries.count()
    my_verified_answers = user_queries.filter(
        status=QuestionAnswer.Status.ANSWERED
    ).count()

    available_manuals_count = Manual.objects.filter(
        indexing_status=Manual.IndexingStatus.INDEXED
    ).count()

    recent_questions = (
        user_queries.select_related("machine")
        .order_by("-created_at")[:5]
    )

    context = {
        "active_machines_count": active_machines_count,
        "machines": machines,
        "my_questions_count": my_questions_count,
        "my_verified_answers": my_verified_answers,
        "available_manuals_count": available_manuals_count,
        "recent_questions": recent_questions,
    }
    return render(request, "dashboard/engineer_dashboard.html", context)


@supervisor_required
def supervisor_dashboard(request):
    """
    Plant Supervision & Audit Console.
    Supplies plant-wide maintenance inquiry oversight, knowledge coverage ratio,
    and equipment query distribution.
    """
    all_questions = QuestionAnswer.objects.all()
    total_questions = all_questions.count()
    answered_questions = all_questions.filter(
        status=QuestionAnswer.Status.ANSWERED
    ).count()
    unanswered_questions = all_questions.filter(
        status__in=[QuestionAnswer.Status.INSUFFICIENT, QuestionAnswer.Status.CONFLICTING]
    ).count()

    if total_questions > 0:
        coverage_ratio = round((answered_questions / total_questions) * 100, 1)
    else:
        coverage_ratio = 100.0

    # Equipment query distribution breakdown
    machine_activity = []
    for machine in Machine.objects.all():
        q_qs = QuestionAnswer.objects.filter(machine=machine)
        total = q_qs.count()
        if total > 0 or machine.is_active:
            machine_activity.append({
                "machine": machine,
                "name": machine.name,
                "model_number": machine.model_number,
                "total_queries": total,
                "answered_count": q_qs.filter(status=QuestionAnswer.Status.ANSWERED).count(),
                "insufficient_count": q_qs.filter(status=QuestionAnswer.Status.INSUFFICIENT).count(),
                "conflicting_count": q_qs.filter(status=QuestionAnswer.Status.CONFLICTING).count(),
            })

    machine_activity.sort(key=lambda m: m["total_queries"], reverse=True)

    recent_questions = (
        QuestionAnswer.objects.select_related("machine", "engineer")
        .order_by("-created_at")[:10]
    )

    context = {
        "total_questions": total_questions,
        "answered_questions": answered_questions,
        "unanswered_questions": unanswered_questions,
        "coverage_ratio": coverage_ratio,
        "machine_activity": machine_activity,
        "recent_questions": recent_questions,
    }
    return render(request, "dashboard/supervisor_dashboard.html", context)
