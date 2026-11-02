"""
Automated unit tests for the dashboard application.
Verifies role-based dispatching, KPI calculations, and context provisioning across
Admin, Supervisor, and Engineer dashboards.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from machines.models import Machine
from manuals.models import Manual
from assistant.models import QuestionAnswer


class DashboardViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Groups
        self.admin_group, _ = Group.objects.get_or_create(name="Administrator")
        self.supervisor_group, _ = Group.objects.get_or_create(name="Supervisor")
        self.engineer_group, _ = Group.objects.get_or_create(name="Engineer")

        # Users
        self.admin_user = User.objects.create_user(
            username="admin_ops", password="password123"
        )
        self.admin_user.groups.add(self.admin_group)

        self.supervisor_user = User.objects.create_user(
            username="sup_plant", password="password123"
        )
        self.supervisor_user.groups.add(self.supervisor_group)

        self.engineer_user = User.objects.create_user(
            username="eng_field", password="password123"
        )
        self.engineer_user.groups.add(self.engineer_group)

        # Machines
        self.m1 = Machine.objects.create(name="AC90 Grinder", model_number="M-AC90", is_active=True)
        self.m2 = Machine.objects.create(name="HP200 Press", model_number="M-HP200", is_active=True)
        self.m_inactive = Machine.objects.create(name="Old Lathe", model_number="M-OLD", is_active=False)

        # Manuals
        self.man1 = Manual.objects.create(
            machine=self.m1,
            document_id="DOC-AC90-1",
            title="AC90 Maintenance Manual",
            revision="1.0",
            pdf_file="manuals/sample.pdf",
            indexing_status=Manual.IndexingStatus.INDEXED,
            total_pages=15,
            total_chunks=30,
        )
        self.man2 = Manual.objects.create(
            machine=self.m2,
            document_id="DOC-HP200-1",
            title="HP200 Operator Guide",
            revision="2.0",
            pdf_file="manuals/sample2.pdf",
            indexing_status=Manual.IndexingStatus.FAILED,
            total_pages=0,
            total_chunks=0,
        )

        # Questions
        self.q1 = QuestionAnswer.objects.create(
            engineer=self.engineer_user,
            machine=self.m1,
            question="What is the spindle torque?",
            answer="Torque is 45 Nm.",
            status=QuestionAnswer.Status.ANSWERED,
            citations=[{"document_id": "DOC-AC90-1", "page_number": 5}],
        )
        self.q2 = QuestionAnswer.objects.create(
            engineer=self.engineer_user,
            machine=self.m2,
            question="What is hydraulic threshold?",
            answer="Information insufficient.",
            status=QuestionAnswer.Status.INSUFFICIENT,
            citations=[],
        )

    def test_dashboard_home_redirects_by_role(self):
        # Admin
        self.client.login(username="admin_ops", password="password123")
        res_admin = self.client.get(reverse("dashboard"))
        self.assertRedirects(res_admin, reverse("admin_dashboard"))

        # Supervisor
        self.client.login(username="sup_plant", password="password123")
        res_sup = self.client.get(reverse("dashboard"))
        self.assertRedirects(res_sup, reverse("supervisor_dashboard"))

        # Engineer
        self.client.login(username="eng_field", password="password123")
        res_eng = self.client.get(reverse("dashboard"))
        self.assertRedirects(res_eng, reverse("engineer_dashboard"))

    def test_admin_dashboard_kpis_and_context(self):
        self.client.login(username="admin_ops", password="password123")
        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_machines"], 3)
        self.assertEqual(response.context["total_manuals"], 2)
        self.assertEqual(response.context["indexed_manuals"], 1)
        self.assertEqual(response.context["failed_manuals"], 1)

        # HTML KPI checks
        self.assertContains(response, "Registered Machines")
        self.assertContains(response, "Ingested Manuals")
        self.assertContains(response, "ChromaDB Chunks")
        self.assertContains(response, "Pipeline Reliability")
        self.assertContains(response, "AC90 Maintenance Manual")

    def test_supervisor_dashboard_kpis_and_context(self):
        self.client.login(username="sup_plant", password="password123")
        response = self.client.get(reverse("supervisor_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_questions"], 2)
        self.assertEqual(response.context["answered_questions"], 1)
        self.assertEqual(response.context["unanswered_questions"], 1)
        self.assertEqual(response.context["coverage_ratio"], 50.0)

        # HTML KPI checks
        self.assertContains(response, "Total Inquiries Logged")
        self.assertContains(response, "Fully Answered")
        self.assertContains(response, "Unanswered / Insufficient")
        self.assertContains(response, "Knowledge Coverage Ratio")
        self.assertContains(response, "50.0%")

    def test_engineer_dashboard_kpis_and_context(self):
        self.client.login(username="eng_field", password="password123")
        response = self.client.get(reverse("engineer_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["active_machines_count"], 2)
        self.assertEqual(response.context["my_questions_count"], 2)
        self.assertEqual(response.context["my_verified_answers"], 1)
        self.assertEqual(response.context["available_manuals_count"], 1)

        # HTML KPI checks
        self.assertContains(response, "Active Machinery Fleet")
        self.assertContains(response, "My Technical Inquiries")
        self.assertContains(response, "Verified Answers")
        self.assertContains(response, "Ingested Manuals")
        self.assertContains(response, "AC90 Grinder")

    def test_dashboard_permission_barriers(self):
        # Engineer trying to access Admin dashboard -> 403
        self.client.login(username="eng_field", password="password123")
        res_admin = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(res_admin.status_code, 403)

        # Engineer trying to access Supervisor dashboard -> 403
        res_sup = self.client.get(reverse("supervisor_dashboard"))
        self.assertEqual(res_sup.status_code, 403)
