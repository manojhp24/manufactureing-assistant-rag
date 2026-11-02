from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date

from accounts.permissions import engineer_required, supervisor_required
from machines.models import Machine
from .models import QuestionAnswer
from .services import ask_manual_assistant


@engineer_required
def chat_view(request):
    """
    Interactive AI maintenance assistant chat terminal.
    Supplies active equipment fleet to populate target machine dropdown.
    Isolates RAG context to selected machine's technical manuals.
    """
    machines = Machine.objects.filter(is_active=True).prefetch_related("manuals")

    machine_id = request.POST.get("machine_id") or request.GET.get("machine_id")
    selected_machine = None

    if machine_id:
        try:
            selected_machine = Machine.objects.filter(id=machine_id, is_active=True).first()
        except (ValueError, TypeError):
            selected_machine = None

    if request.method == "POST":
        question_text = request.POST.get("question", "").strip()

        if not selected_machine:
            messages.error(request, "Please select an active target machine before asking a question.")
        elif not question_text:
            messages.error(request, "Question cannot be blank.")
        else:
            try:
                result = ask_manual_assistant(
                    question=question_text,
                    machine_id=selected_machine.model_number,
                )

                answer = result.get("answer", "")
                rag_status = str(result.get("status", "")).lower()

                if "conflict" in rag_status:
                    status = QuestionAnswer.Status.CONFLICTING
                elif "insufficient" in rag_status:
                    status = QuestionAnswer.Status.INSUFFICIENT
                else:
                    status = QuestionAnswer.Status.ANSWERED

                citations = result.get("citations", [])

                QuestionAnswer.objects.create(
                    engineer=request.user,
                    machine=selected_machine,
                    question=question_text,
                    answer=answer,
                    status=status,
                    citations=citations,
                )

            except Exception as error:
                messages.error(request, f"Unable to generate an answer: {error}")

    # Load conversation history for current terminal view
    if selected_machine:
        conversation = list(
            QuestionAnswer.objects.filter(
                engineer=request.user,
                machine=selected_machine,
            ).order_by("created_at")
        )
    else:
        conversation = list(
            QuestionAnswer.objects.filter(
                engineer=request.user,
            ).order_by("-created_at")[:5]
        )
        conversation.reverse()

    latest_citations = []
    if conversation and conversation[-1].citations:
        latest_citations = conversation[-1].citations

    return render(
        request,
        "assistant/chat.html",
        {
            "machines": machines,
            "selected_machine": selected_machine,
            "conversation": conversation,
            "latest_citations": latest_citations,
        },
    )


# Backwards compatibility alias
ask_question = chat_view


@engineer_required
def history_view(request):
    """
    Operator inquiry audit history.
    Lists past questions, answers, and verification statuses for current operator.
    """
    questions_qs = QuestionAnswer.objects.filter(
        engineer=request.user
    ).select_related("machine").order_by("-created_at")

    paginator = Paginator(questions_qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "assistant/history.html",
        {
            "questions": page_obj.object_list,
            "page_obj": page_obj,
        },
    )


@supervisor_required
def supervisor_history_view(request):
    """
    Plant supervisor audit log of all maintenance inquiries across all operators.
    Supports filtering by machine, answer verification status, and logged date.
    """
    queryset = QuestionAnswer.objects.select_related("machine", "engineer").order_by("-created_at")

    filter_machine = request.GET.get("machine", "").strip()
    filter_status = request.GET.get("status", "").strip()
    filter_date = request.GET.get("date", "").strip()

    if filter_machine:
        queryset = queryset.filter(machine_id=filter_machine)

    if filter_status:
        if filter_status in ["insufficient", "insufficient_information"]:
            queryset = queryset.filter(status=QuestionAnswer.Status.INSUFFICIENT)
        elif filter_status in ["conflicting", "conflicting_information"]:
            queryset = queryset.filter(status=QuestionAnswer.Status.CONFLICTING)
        else:
            queryset = queryset.filter(status=filter_status)

    if filter_date:
        parsed = parse_date(filter_date)
        if parsed:
            queryset = queryset.filter(created_at__date=parsed)

    machines = Machine.objects.all()

    paginator = Paginator(queryset, 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(
        request,
        "assistant/supervisor_history.html",
        {
            "questions": page_obj.object_list,
            "page_obj": page_obj,
            "machines": machines,
        },
    )


@engineer_required
def answer_detail_view(request, pk):
    """
    Detailed evidence inspection view for a single inquiry record.
    Displays original prompt, full generated answer, and exact citations.
    """
    query = get_object_or_404(
        QuestionAnswer.objects.select_related("machine", "engineer"),
        pk=pk,
    )

    return render(
        request,
        "assistant/answer_detail.html",
        {
            "query": query,
            "citations": query.citations,
        },
    )
