"""
Unit tests for the assistant application.
Verifies chat terminal view, machine dropdown population, isolation, history, and supervisor auditing.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from machines.models import Machine
from assistant.models import QuestionAnswer


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

        self.supervisor_user = User.objects.create_user(
            username="sup_plant", password="password123"
        )
        self.supervisor_user.groups.add(self.supervisor_group)

        # Machines
        self.m1 = Machine.objects.create(name="AC90 Grinder", model_number="M-AC90", is_active=True)
        self.m2 = Machine.objects.create(name="HP200 Press", model_number="M-HP200", is_active=True)
        self.m_inactive = Machine.objects.create(name="Old Lathe", model_number="M-OLD", is_active=False)

    def test_chat_view_populates_active_machines_in_dropdown(self):
        """Verify that active machines are passed to the chat context to populate the target machine dropdown."""
        self.client.login(username="eng_field", password="password123")
        response = self.client.get(reverse("assistant_chat"))

        self.assertEqual(response.status_code, 200)
        self.assertIn("machines", response.context)
        machines = list(response.context["machines"])

        # Active machines must be present
        self.assertIn(self.m1, machines)
        self.assertIn(self.m2, machines)
        # Inactive machines must NOT be present
        self.assertNotIn(self.m_inactive, machines)

        # HTML should contain option tags for machines
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
        # Create a sample QA
        QuestionAnswer.objects.create(
            engineer=self.engineer_user,
            machine=self.m1,
            question="What is the torque spec?",
            answer="Torque specification is 45 Nm.",
            status=QuestionAnswer.Status.ANSWERED,
            citations=[{"document_id": "DOC-1", "page_number": 12, "text_passage": "Torque is 45 Nm"}],
        )

        self.client.login(username="eng_field", password="password123")
        response = self.client.get(reverse("assistant_history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "What is the torque spec?")
        self.assertContains(response, "Torque specification is 45 Nm.")

    def test_supervisor_history_view_permissions(self):
        # Engineer blocked
        self.client.login(username="eng_field", password="password123")
        res_eng = self.client.get(reverse("supervisor_history"))
        self.assertEqual(res_eng.status_code, 403)

        # Supervisor allowed
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
            citations=[{"document_id": "DOC-AC90", "page_number": 4, "text_passage": "Bearing clearance is 0.02mm"}],
        )

        self.client.login(username="eng_field", password="password123")
        response = self.client.get(reverse("answer_detail", kwargs={"pk": qa.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "How to inspect spindle bearings?")
        self.assertContains(response, "Check bearing clearance with a dial indicator.")
        self.assertContains(response, "Bearing clearance is 0.02mm")
