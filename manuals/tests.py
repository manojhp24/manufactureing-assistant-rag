"""
Automated unit and integration tests for the manuals application.
Tests cover RBAC restrictions, upload workflow, mock RAG indexing,
file validation, filtering, search, and template rendering.
"""
from unittest.mock import patch
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from machines.models import Machine
from manuals.models import Manual
from manuals.forms import ManualUploadForm


class ManualsWorkflowTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Groups & Roles
        self.admin_group, _ = Group.objects.get_or_create(name="Administrator")
        self.supervisor_group, _ = Group.objects.get_or_create(name="Supervisor")
        self.engineer_group, _ = Group.objects.get_or_create(name="Engineer")

        # Admin User
        self.admin = User.objects.create_user(username="admin_tech", password="password123")
        self.admin.groups.add(self.admin_group)

        # Engineer User (non-admin)
        self.engineer = User.objects.create_user(username="eng_field", password="password123")
        self.engineer.groups.add(self.engineer_group)

        # Machinery
        self.machine1 = Machine.objects.create(name="CNC 5-Axis Mill", model_number="M-CNC5X", is_active=True)
        self.machine2 = Machine.objects.create(name="Robotic Welder", model_number="M-ROBOW", is_active=True)

        # Existing Manual
        self.sample_pdf = SimpleUploadedFile(
            "maintenance_guide.pdf",
            b"%PDF-1.4 sample pdf content stream",
            content_type="application/pdf"
        )
        self.manual = Manual.objects.create(
            machine=self.machine1,
            document_id="DOC-CNC-001",
            title="CNC 5-Axis Milling Manual",
            revision="1.0",
            pdf_file=self.sample_pdf,
            indexing_status=Manual.IndexingStatus.INDEXED,
            total_pages=24,
            total_chunks=48,
        )

    def test_upload_manual_rbac_access(self):
        """Unauthenticated and non-admin users must be blocked from upload endpoint."""
        url = reverse("upload_manual")

        # Unauthenticated redirects to login
        res = self.client.get(url)
        self.assertEqual(res.status_code, 302)

        # Engineer receives 403 Forbidden
        self.client.login(username="eng_field", password="password123")
        res_eng = self.client.get(url)
        self.assertEqual(res_eng.status_code, 403)

        # Admin receives 200 OK
        self.client.login(username="admin_tech", password="password123")
        res_admin = self.client.get(url)
        self.assertEqual(res_admin.status_code, 200)
        self.assertTemplateUsed(res_admin, "manuals/manual_upload.html")

    def test_upload_manual_preselect_machine(self):
        """Passing ?machine=<id> should pre-select the machine in the form."""
        self.client.login(username="admin_tech", password="password123")
        url = reverse("upload_manual") + f"?machine={self.machine2.id}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        form = response.context["form"]
        self.assertEqual(str(form.initial.get("machine")), str(self.machine2.id))

    @patch("manuals.views.index_manual")
    def test_upload_manual_successful_post(self, mock_indexer):
        """Posting valid PDF manual triggers save and indexer dispatch."""
        mock_indexer.return_value = {"total_pages": 12, "total_chunks": 24}

        self.client.login(username="admin_tech", password="password123")
        new_pdf = SimpleUploadedFile(
            "welder_schematic.pdf",
            b"%PDF-1.4 binary data stream",
            content_type="application/pdf"
        )

        payload = {
            "machine": self.machine2.id,
            "document_id": "MAN-ROBO-99",
            "title": "Robotic Welder Technical Schematics",
            "revision": "2.1",
            "pdf_file": new_pdf,
        }

        response = self.client.post(reverse("upload_manual"), payload, follow=True)
        self.assertEqual(response.status_code, 200)

        # Verify DB persistence
        created = Manual.objects.filter(document_id="MAN-ROBO-99").first()
        self.assertIsNotNone(created)
        self.assertEqual(created.title, "Robotic Welder Technical Schematics")
        self.assertEqual(created.revision, "2.1")
        mock_indexer.assert_called_once()

    def test_form_validation_rejects_non_pdf(self):
        """Form must reject files that do not have .pdf extension."""
        text_file = SimpleUploadedFile(
            "manual.txt",
            b"Plain text manual notes",
            content_type="text/plain"
        )
        form = ManualUploadForm(
            data={
                "machine": self.machine1.id,
                "document_id": "DOC-TXT-01",
                "title": "Text File Manual",
                "revision": "1.0",
            },
            files={"pdf_file": text_file}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("pdf_file", form.errors)
        self.assertIn("Only PDF technical manual files are supported", form.errors["pdf_file"][0])

    def test_manual_list_filtering_and_search(self):
        """Manual list view supports query search and machine filtering."""
        self.client.login(username="admin_tech", password="password123")
        url = reverse("manual_list")

        # 1. Base list
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(len(res.context["manuals"]), 1)
        self.assertEqual(res.context["total_count"], 1)

        # 2. Filter by machine1
        res_m1 = self.client.get(url + f"?machine={self.machine1.id}")
        self.assertEqual(len(res_m1.context["manuals"]), 1)

        # 3. Filter by machine2 (should be 0)
        res_m2 = self.client.get(url + f"?machine={self.machine2.id}")
        self.assertEqual(len(res_m2.context["manuals"]), 0)

        # 4. Search query
        res_q = self.client.get(url + "?q=CNC")
        self.assertEqual(len(res_q.context["manuals"]), 1)

        res_q_nomatch = self.client.get(url + "?q=NonExistentQueryXYZ")
        self.assertEqual(len(res_q_nomatch.context["manuals"]), 0)
