import os
from pathlib import Path

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.utils.dateparse import parse_date
from django.http import FileResponse, Http404
from django.core.exceptions import PermissionDenied

from accounts.permissions import engineer_required, supervisor_required, is_administrator, is_engineer, is_supervisor
from machines.models import Machine
from manuals.models import Manual
from .models import QuestionAnswer
from .services import ask_manual_assistant
from .pdf_highlighter import PdfHighlighter


@engineer_required
def chat_view(request):
    """
    Interactive AI maintenance assistant chat terminal.
    Supplies active equipment fleet to populate target machine dropdown.
    Isolates RAG context to selected machine's technical manuals.
    Maintains sticky selected machine state across requests.
    """
    machines = Machine.objects.filter(is_active=True).prefetch_related("manuals")

    machine_id = request.POST.get("machine_id") or request.GET.get("machine_id")
    selected_machine = None

    if machine_id:
        try:
            selected_machine = Machine.objects.filter(id=machine_id, is_active=True).first()
        except (ValueError, TypeError):
            selected_machine = None

    # If machine was not explicitly passed in GET/POST, maintain state from session or recent activity
    if not selected_machine and machine_id != "":
        # 1. Check session state
        session_machine_id = request.session.get("last_selected_machine_id")
        if session_machine_id:
            selected_machine = Machine.objects.filter(id=session_machine_id, is_active=True).first()

        # 2. Check engineer's most recent inquiry
        if not selected_machine:
            last_qa = QuestionAnswer.objects.filter(engineer=request.user).order_by("-created_at").first()
            if last_qa and last_qa.machine and last_qa.machine.is_active:
                selected_machine = last_qa.machine

        # 3. Default to first active machine in fleet
        if not selected_machine and machines.exists():
            selected_machine = machines.first()

    # Persist the active machine in session
    if selected_machine:
        request.session["last_selected_machine_id"] = selected_machine.id

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
            ).order_by("-created_at")[:10]
        )
        conversation.reverse()

    latest_citations = []
    latest_question_id = None
    if conversation and conversation[-1].citations:
        latest_citations = conversation[-1].citations
        latest_question_id = conversation[-1].id

    return render(
        request,
        "assistant/chat.html",
        {
            "machines": machines,
            "selected_machine": selected_machine,
            "conversation": conversation,
            "latest_citations": latest_citations,
            "latest_question_id": latest_question_id,
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


def _check_citation_access(request, query, citation_index):
    """
    Validate that the requesting user is authorized to view this citation.

    Returns (ok: bool, error_message: str | None).
    """
    if not request.user.is_authenticated:
        return False, "Authentication required."

    user = request.user
    is_admin = is_administrator(user)
    is_sup = is_supervisor(user)
    is_eng = is_engineer(user)

    if not (is_admin or is_sup or is_eng):
        return False, "Access denied: you do not have clearance for this record."

    # Engineers can only access their own questions
    if is_eng and not is_sup and not is_admin:
        if query.engineer_id != user.id:
            return False, "Access denied: this record belongs to another engineer."

    # Supervisors can access permitted question history (any engineer's questions)
    if is_sup and not is_admin:
        # Supervisors can access all questions - no restriction
        pass

    # Administrators can access authorized records
    if is_admin:
        pass

    # Validate citation index
    citations = query.citations or []
    if not isinstance(citations, list) or citation_index < 0 or citation_index >= len(citations):
        return False, f"Invalid citation index: {citation_index}."

    return True, None


def _resolve_manual(machine, citation):
    """
    Resolve the correct Manual record using the document ID and selected machine.
    Guarantees isolation: ONLY returns a manual belonging to the given machine.
    """
    if not machine:
        return None

    document_id = str(citation.get("document_id") or "").strip()
    revision = str(citation.get("revision") or "").strip()
    source_name = str(citation.get("source") or "").strip()

    manuals = Manual.objects.filter(machine=machine)
    if not manuals.exists():
        return None

    # Strategy 1: Exact match on document_id and revision
    if document_id and revision:
        m = manuals.filter(document_id__iexact=document_id, revision__iexact=revision).first()
        if m:
            return m

    # Strategy 2: Match by document_id alone (case-insensitive)
    if document_id:
        m = manuals.filter(document_id__iexact=document_id).first()
        if m:
            return m

    # Strategy 3: Match by source filename (e.g. AC90_Operations_Maintenance_Rev1_0.pdf)
    if source_name:
        clean_name = os.path.basename(source_name).lower()
        for m in manuals:
            if m.pdf_file and clean_name in m.pdf_file.name.lower():
                return m

    # Strategy 4: Normalized match on document_id against manual document_id or filename
    if document_id:
        norm_doc = document_id.replace("-", "").replace("_", "").lower()
        for m in manuals:
            m_norm = m.document_id.replace("-", "").replace("_", "").lower()
            m_file = os.path.basename(m.pdf_file.name).lower() if m.pdf_file else ""
            if norm_doc in m_norm or m_norm in norm_doc or norm_doc in m_file:
                return m

    # Strategy 5: If there is only one manual for this machine, it is this machine's manual
    if manuals.count() == 1:
        return manuals.first()

    # Strategy 6: Match by revision
    if revision:
        m = manuals.filter(revision__iexact=revision).first()
        if m:
            return m

    return manuals.first()


@engineer_required
def citation_pdf_view(request, question_id, citation_index):
    """
    Protected endpoint to open a highlighted PDF for a citation.

    URL: /assistant/citation/<question_id>/<citation_index>/

    Generates (or reuses) a highlighted PDF copy of the cited manual page,
    then streams it back to the authorized user.
    """
    try:
        question_id = int(question_id)
        citation_index = int(citation_index)
    except (ValueError, TypeError):
        raise Http404("Invalid citation reference.")

    query = get_object_or_404(
        QuestionAnswer.objects.select_related("machine", "engineer"),
        pk=question_id,
    )

    # Authorization check
    ok, error = _check_citation_access(request, query, citation_index)
    if not ok:
        raise PermissionDenied(error)

    citations = query.citations or []
    citation = citations[citation_index]

    # Validate citation has enough info
    document_id = citation.get("document_id")
    page_number = citation.get("page_number")
    text_passage = citation.get("text_passage", "")

    if not document_id or not page_number:
        raise Http404("Citation metadata is incomplete.")

    # Resolve the correct Manual record for this machine
    manual = _resolve_manual(query.machine, citation)
    if not manual:
        raise Http404("Cited manual not found for this machine.")

    # Strictly verify the manual belongs to the machine associated with the question
    if manual.machine_id != query.machine_id:
        raise Http404("Manual does not belong to the question's machine.")

    # If text_passage is empty, attempt to recover chunk text from ChromaDB
    if not text_passage:
        try:
            from rag.vectorstore.chroma_store import get_vectorstore
            vs = get_vectorstore()
            chunks_data = vs._collection.get(
                where={"machine_id": query.machine.model_number},
                include=["documents", "metadatas"]
            )
            for m_meta, m_doc in zip(chunks_data.get("metadatas", []), chunks_data.get("documents", [])):
                if m_meta.get("page_number") == page_number:
                    text_passage = m_doc
                    break
        except Exception:
            pass

    highlighter = PdfHighlighter()
    result = highlighter.highlight_citation(
        manual=manual,
        page_number=page_number,
        text_passage=text_passage,
        question_id=question_id,
        citation_index=citation_index,
    )

    if result["fallback"] or not result["highlighted_path"]:
        # Fallback: serve the original PDF page (no highlighting)
        return _serve_original_pdf(manual, page_number, result.get("error"))

    return _serve_pdf_file(result["highlighted_path"])


def _serve_pdf_file(file_path: str) -> FileResponse:
    """Stream a PDF file to the client."""
    if not os.path.exists(file_path):
        raise Http404("Highlighted PDF not found.")

    response = FileResponse(open(file_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = f'inline; filename="{os.path.basename(file_path)}"'
    response["Cache-Control"] = "private, max-age=3600"
    return response


def _serve_original_pdf(manual, page_number: int, error: str | None = None) -> FileResponse:
    """Fallback: serve the original PDF (no highlighting applied)."""
    pdf_path = Path(manual.pdf_file.path)

    if not pdf_path.exists():
        raise Http404("Original PDF not found.")

    response = FileResponse(open(pdf_path, "rb"), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'inline; filename="{os.path.basename(pdf_path)}"'
    )
    response["Cache-Control"] = "private, max-age=3600"
    if error:
        response["X-Highlight-Status"] = "fallback"
        response["X-Highlight-Error"] = error
    return response
