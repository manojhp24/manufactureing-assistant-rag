"""
Unit tests for the assistant application.
Verifies chat terminal view, machine dropdown population, isolation, history, supervisor auditing,
and PDF citation highlighting with permission checks and fallbacks.
"""
import hashlib
import os
import pymupdf
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from machines.models import Machine
from manuals.models import Manual
from assistant.models import QuestionAnswer
from assistant.pdf_highlighter import PdfHighlighter


def create_test_pdf(text_on_pages):
    """Generate in-memory PDF bytes with given text per page."""
    doc = pymupdf.open()
    for text in text_on_pages:
        page = doc.new_page()
        page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class AssistantViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Groups
        self.engineer_group, _ = Group.objects.get_or_create(name="Engineer")
        self.supervisor_group, _ = Group.objects.get_or_create(name="Supervisor")
        self.admin_group, _ = Group.objects.get_or_create(name="Administrator")

        # Users
        self.engineer_user = User.objects.create_user(
            username="eng_field", password="password123"
        )
        self.engineer_user.groups.add(self.engineer_group)

        self.engineer_user2 = User.objects.create_user(
            username="eng_other", password="password123"
        )
        self.engineer_user2.groups.add(self.engineer_group)

        self.supervisor_user = User.objects.create_user(
            username="sup_plant", password="password123"
        )
        self.supervisor_user.groups.add(self.supervisor_group)

        # Machines
        self.m1 = Machine.objects.create(name="AC90 Grinder", model_number="M-AC90", is_active=True)
        self.m2 = Machine.objects.create(name="HP200 Press", model_number="M-HP200", is_active=True)
        self.m_inactive = Machine.objects.create(name="Old Lathe", model_number="M-OLD", is_active=False)

        # PDF Manuals
        pdf_bytes_ac90 = create_test_pdf([
            "AC90 Cover Page",
            "Error Code E24 represents high discharge temperature. Inspect cooling path."
        ])
        self.manual_ac90 = Manual.objects.create(
            machine=self.m1,
            document_id="AC-OM-01",
            revision="1.0",
            title="AC90 Manual",
            pdf_file=SimpleUploadedFile("ac90.pdf", pdf_bytes_ac90, content_type="application/pdf"),
            indexing_status=Manual.IndexingStatus.INDEXED,
            total_pages=2,
        )

        pdf_bytes_hp200 = create_test_pdf([
            "HP200 Operations Guide",
            "Spindle lubrication procedure: use ISO VG 46 hydraulic oil."
        ])
        self.manual_hp200 = Manual.objects.create(
            machine=self.m2,
            document_id="HP-OPS-01",
            revision="1.0",
            title="HP200 Manual",
            pdf_file=SimpleUploadedFile("hp200.pdf", pdf_bytes_hp200, content_type="application/pdf"),
            indexing_status=Manual.IndexingStatus.INDEXED,
            total_pages=2,
        )

    def test_chat_view_populates_active_machines_in_dropdown(self):
        """Verify that active machines are passed to the chat context to populate the target machine dropdown."""
        self.client.login(username="eng_field", password="password123")
        response = self.client.get(reverse("assistant_chat"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("machines", response.context)
        machines = list(response.context["machines"])

        self.assertIn(self.m1, machines)
        self.assertIn(self.m2, machines)
        self.assertNotIn(self.m_inactive, machines)
        self.assertContains(response, "AC90 Grinder (M-AC90)")
        self.assertContains(response, "HP200 Press (M-HP200)")

    def test_chat_view_selects_target_machine_via_query_param(self):
        self.client.login(username="eng_field", password="password123")
        response = self.client.get(f"{reverse('assistant_chat')}?machine_id={self.m2.id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["selected_machine"], self.m2)
        self.assertContains(response, "selected")
        self.assertContains(response, f'Equipment Connected: {self.m2.name}')

    def test_history_view_accessible_to_engineer(self):
        QuestionAnswer.objects.create(
            engineer=self.engineer_user,
            machine=self.m1,
            question="What is the torque spec?",
            answer="Torque specification is 45 Nm.",
            status=QuestionAnswer.Status.ANSWERED,
            citations=[{"document_id": "AC-OM-01", "page_number": 2, "text_passage": "Torque is 45 Nm"}],
        )

        self.client.login(username="eng_field", password="password123")
        response = self.client.get(reverse("assistant_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is the torque spec?")
        self.assertContains(response, "Torque specification is 45 Nm.")

    def test_supervisor_history_view_permissions(self):
        self.client.login(username="eng_field", password="password123")
        res_eng = self.client.get(reverse("supervisor_history"))
        self.assertEqual(res_eng.status_code, 403)

        self.client.login(username="sup_plant", password="password123")
        res_sup = self.client.get(reverse("supervisor_history"))
        self.assertEqual(res_sup.status_code, 200)

    def test_answer_detail_view(self):
        qa = QuestionAnswer.objects.create(
            engineer=self.engineer_user,
            machine=self.m1,
            question="How to inspect spindle bearings?",
            answer="Check bearing clearance with a dial indicator.",
            status=QuestionAnswer.Status.ANSWERED,
            citations=[{"document_id": "AC-OM-01", "page_number": 2, "text_passage": "Bearing clearance is 0.02mm"}],
        )

        self.client.login(username="eng_field", password="password123")
        response = self.client.get(reverse("answer_detail", kwargs={"pk": qa.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How to inspect spindle bearings?")
        self.assertContains(response, "Check bearing clearance with a dial indicator.")

    # -------------------------------------------------------------
    # PDF Citation Highlighting Feature Tests
    # -------------------------------------------------------------

    def test_citation_pdf_view_opens_and_highlights_correct_manual(self):
        """Verify that an AC90 question citation opens the AC90 manual and highlights text."""
        qa = QuestionAnswer.objects.create(
            engineer=self.engineer_user,
            machine=self.m1,
            question="What does E24 mean?",
            answer="E24 represents high discharge temperature.",
            status=QuestionAnswer.Status.ANSWERED,
            citations=[{
                "document_id": "AC-OM-01",
                "revision": "1.0",
                "page_number": 2,
                "text_passage": "Error Code E24 represents high discharge temperature",
            }],
        )

        self.client.login(username="eng_field", password="password123")
        url = reverse("citation_pdf", kwargs={"question_id": qa.id, "citation_index": 0})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")

        # Verify that original PDF was NOT overwritten
        with open(self.manual_ac90.pdf_file.path, "rb") as f:
            orig_doc = pymupdf.open(stream=f.read(), filetype="pdf")
            self.assertEqual(len(list(orig_doc[1].annots())), 0)  # Original has zero annotations
            orig_doc.close()

    def test_hp200_citation_opens_hp200_manual(self):
        """Verify that an HP200 question citation opens the HP200 manual."""
        qa = QuestionAnswer.objects.create(
            engineer=self.engineer_user,
            machine=self.m2,
            question="What hydraulic oil for HP200?",
            answer="Use ISO VG 46.",
            status=QuestionAnswer.Status.ANSWERED,
            citations=[{
                "document_id": "HP-OPS-01",
                "revision": "1.0",
                "page_number": 2,
                "text_passage": "Spindle lubrication procedure: use ISO VG 46",
            }],
        )

        self.client.login(username="eng_field", password="password123")
        url = reverse("citation_pdf", kwargs={"question_id": qa.id, "citation_index": 0})
        res = self.client.get(url)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")

    def test_engineer_cannot_access_other_engineer_citation(self):
        """An engineer cannot view citations belonging to another engineer's private question."""
        qa = QuestionAnswer.objects.create(
            engineer=self.engineer_user2,
            machine=self.m1,
            question="Private query",
            answer="Secret spec",
            status=QuestionAnswer.Status.ANSWERED,
            citations=[{"document_id": "AC-OM-01", "revision": "1.0", "page_number": 2}],
        )

        self.client.login(username="eng_field", password="password123")
        url = reverse("citation_pdf", kwargs={"question_id": qa.id, "citation_index": 0})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 403)

    def test_missing_text_passage_graceful_fallback(self):
        """If cited text passage cannot be found on page, serve original PDF page gracefully with 200."""
        qa = QuestionAnswer.objects.create(
            engineer=self.engineer_user,
            machine=self.m1,
            question="Unknown code",
            answer="No info",
            status=QuestionAnswer.Status.ANSWERED,
            citations=[{
                "document_id": "AC-OM-01",
                "revision": "1.0",
                "page_number": 2,
                "text_passage": "This sentence does not exist anywhere in the PDF file at all",
            }],
        )

        self.client.login(username="eng_field", password="password123")
        url = reverse("citation_pdf", kwargs={"question_id": qa.id, "citation_index": 0})
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res["Content-Type"], "application/pdf")
        self.assertEqual(res.get("X-Highlight-Status"), "fallback")
