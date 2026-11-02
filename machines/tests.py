"""
Unit tests for the machines application.
Covers Machine model, MachineForm validation, view permissions, ORM annotations, and search filters.
"""
from django.test import TestCase, Client
from django.contrib.auth.models import User, Group
from django.urls import reverse
from django.core.exceptions import PermissionDenied
from machines.models import Machine
from machines.forms import MachineForm
from manuals.models import Manual


class MachineModelTests(TestCase):
    def test_machine_string_representation(self):
        machine = Machine.objects.create(
            name="CNC 5-Axis Milling Center",
            model_number="CNC-5X-200",
            description="Cell 4 Milling unit",
        )
        self.assertEqual(str(machine), "CNC 5-Axis Milling Center (CNC-5X-200)")

    def test_default_ordering(self):
        m2 = Machine.objects.create(name="Z-Axis Grinder", model_number="ZG-01")
        m1 = Machine.objects.create(name="Alpha Lathe", model_number="AL-01")
        machines = list(Machine.objects.all())
        self.assertEqual(machines[0], m1)
        self.assertEqual(machines[1], m2)


class MachineFormTests(TestCase):
    def setUp(self):
        self.existing_machine = Machine.objects.create(
            name="Hydraulic Press",
            model_number="HP-500",
            description="500-ton press",
        )

    def test_valid_form(self):
        form = MachineForm(data={
            "name": "Laser Cutter",
            "model_number": "LC-1000",
            "description": "Fiber laser",
            "is_active": True,
        })
        self.assertTrue(form.is_valid())
        machine = form.save()
        self.assertEqual(machine.model_number, "LC-1000")

    def test_model_number_cleaned_to_uppercase_and_trimmed(self):
        form = MachineForm(data={
            "name": "  Robotic Welder  ",
            "model_number": "  rw-400  ",
            "description": "  Automated arc welder  ",
            "is_active": True,
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["name"], "Robotic Welder")
        self.assertEqual(form.cleaned_data["model_number"], "RW-400")
        self.assertEqual(form.cleaned_data["description"], "Automated arc welder")

    def test_duplicate_model_number_rejected_case_insensitively(self):
        form = MachineForm(data={
            "name": "Another Press",
            "model_number": "hp-500",  # lowercase duplicate of HP-500
            "description": "Duplicate test",
            "is_active": True,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("model_number", form.errors)
        self.assertIn("already registered", form.errors["model_number"][0])

    def test_updating_same_instance_model_number_allowed(self):
        form = MachineForm(
            data={
                "name": "Hydraulic Press Updated",
                "model_number": "HP-500",
                "description": "Updated description",
                "is_active": False,
            },
            instance=self.existing_machine,
        )
        self.assertTrue(form.is_valid())

    def test_blank_name_rejected(self):
        form = MachineForm(data={
            "name": "   ",
            "model_number": "NEW-01",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("name", form.errors)


class MachineViewTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Groups
        self.admin_group, _ = Group.objects.get_or_create(name="Administrator")
        self.supervisor_group, _ = Group.objects.get_or_create(name="Supervisor")
        self.engineer_group, _ = Group.objects.get_or_create(name="Engineer")

        # Users
        self.superuser = User.objects.create_superuser(
            username="root_admin", password="password123", email="root@plant.local"
        )
        self.admin_user = User.objects.create_user(
            username="plant_admin", password="password123"
        )
        self.admin_user.groups.add(self.admin_group)

        self.supervisor_user = User.objects.create_user(
            username="plant_sup", password="password123"
        )
        self.supervisor_user.groups.add(self.supervisor_group)

        self.engineer_user = User.objects.create_user(
            username="field_eng", password="password123"
        )
        self.engineer_user.groups.add(self.engineer_group)

        self.unassigned_user = User.objects.create_user(
            username="plain_user", password="password123"
        )

        # Machines
        self.machine1 = Machine.objects.create(
            name="CNC 5-Axis Milling", model_number="CNC-5X", is_active=True
        )
        self.machine2 = Machine.objects.create(
            name="Hydraulic Press", model_number="HP-200", is_active=False
        )

    def test_machine_list_requires_authentication(self):
        response = self.client.get(reverse("machine_list"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login?next=", response.url)

    def test_machine_list_accessible_to_engineers_and_supervisors(self):
        # Engineers can view machine fleet
        self.client.login(username="field_eng", password="password123")
        res = self.client.get(reverse("machine_list"))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, "machines/machine_list.html")
        self.assertContains(res, "CNC 5-Axis Milling")

        # Supervisors can view
        self.client.login(username="plant_sup", password="password123")
        res2 = self.client.get(reverse("machine_list"))
        self.assertEqual(res2.status_code, 200)

        # Superusers can view
        self.client.login(username="root_admin", password="password123")
        res3 = self.client.get(reverse("machine_list"))
        self.assertEqual(res3.status_code, 200)

    def test_machine_list_search_and_filter(self):
        self.client.login(username="field_eng", password="password123")

        # Search by model number
        res = self.client.get(reverse("machine_list") + "?q=CNC-5X")
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "CNC 5-Axis Milling")
        self.assertNotContains(res, "Hydraulic Press")

        # Filter by active
        res_active = self.client.get(reverse("machine_list") + "?status=active")
        self.assertEqual(res_active.status_code, 200)
        self.assertContains(res_active, "CNC 5-Axis Milling")
        self.assertNotContains(res_active, "Hydraulic Press")

        # Filter by inactive
        res_inactive = self.client.get(reverse("machine_list") + "?status=inactive")
        self.assertEqual(res_inactive.status_code, 200)
        self.assertNotContains(res_inactive, "CNC 5-Axis Milling")
        self.assertContains(res_inactive, "Hydraulic Press")

    def test_machine_list_annotates_manuals_count(self):
        # Create a manual for machine1
        from django.core.files.uploadedfile import SimpleUploadedFile
        pdf = SimpleUploadedFile("spec.pdf", b"%PDF-dummy content", content_type="application/pdf")
        Manual.objects.create(
            machine=self.machine1,
            document_id="DOC-CNC-001",
            title="CNC Operator Manual",
            revision="Rev A",
            pdf_file=pdf,
        )

        self.client.login(username="field_eng", password="password123")
        res = self.client.get(reverse("machine_list"))
        self.assertEqual(res.status_code, 200)

        # Confirm manuals_count attribute is present on queryset objects
        machines = res.context["machines"]
        m1 = next(m for m in machines if m.id == self.machine1.id)
        self.assertEqual(m1.manuals_count, 1)

    def test_machine_create_permissions(self):
        # Engineer denied
        self.client.login(username="field_eng", password="password123")
        res_eng = self.client.get(reverse("machine_create"))
        self.assertEqual(res_eng.status_code, 403)

        # Supervisor denied
        self.client.login(username="plant_sup", password="password123")
        res_sup = self.client.get(reverse("machine_create"))
        self.assertEqual(res_sup.status_code, 403)

        # Admin allowed
        self.client.login(username="plant_admin", password="password123")
        res_admin = self.client.get(reverse("machine_create"))
        self.assertEqual(res_admin.status_code, 200)

        # Superuser allowed
        self.client.login(username="root_admin", password="password123")
        res_root = self.client.get(reverse("machine_create"))
        self.assertEqual(res_root.status_code, 200)

    def test_machine_create_post(self):
        self.client.login(username="plant_admin", password="password123")
        response = self.client.post(
            reverse("machine_create"),
            {
                "name": "Industrial 3D Printer",
                "model_number": "3DP-SLS-50",
                "description": "Additive manufacturing cell",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("machine_list"))
        self.assertTrue(Machine.objects.filter(model_number="3DP-SLS-50").exists())

    def test_machine_edit_permissions(self):
        edit_url = reverse("machine_edit", kwargs={"pk": self.machine1.pk})

        # Engineer denied
        self.client.login(username="field_eng", password="password123")
        res_eng = self.client.get(edit_url)
        self.assertEqual(res_eng.status_code, 403)

        # Supervisor allowed
        self.client.login(username="plant_sup", password="password123")
        res_sup = self.client.get(edit_url)
        self.assertEqual(res_sup.status_code, 200)

        # Administrator allowed
        self.client.login(username="plant_admin", password="password123")
        res_admin = self.client.get(edit_url)
        self.assertEqual(res_admin.status_code, 200)

    def test_machine_edit_post(self):
        self.client.login(username="plant_sup", password="password123")
        edit_url = reverse("machine_edit", kwargs={"pk": self.machine1.pk})
        response = self.client.post(
            edit_url,
            {
                "name": "CNC 5-Axis Milling High Speed",
                "model_number": "CNC-5X",
                "description": "Updated cooling system",
                "is_active": True,
            },
        )
        self.assertEqual(response.status_code, 302)
        self.machine1.refresh_from_db()
        self.assertEqual(self.machine1.name, "CNC 5-Axis Milling High Speed")

    def test_machine_toggle_status(self):
        toggle_url = reverse("machine_toggle_status", kwargs={"pk": self.machine1.pk})

        # GET method should be rejected (405)
        self.client.login(username="plant_admin", password="password123")
        res_get = self.client.get(toggle_url)
        self.assertEqual(res_get.status_code, 405)

        # Engineer denied
        self.client.login(username="field_eng", password="password123")
        res_eng = self.client.post(toggle_url)
        self.assertEqual(res_eng.status_code, 403)

        # Admin allowed -> toggle from True to False
        self.client.login(username="plant_admin", password="password123")
        res_post = self.client.post(toggle_url)
        self.assertEqual(res_post.status_code, 302)
        self.machine1.refresh_from_db()
        self.assertFalse(self.machine1.is_active)

        # Toggle back to True
        res_post2 = self.client.post(toggle_url)
        self.assertEqual(res_post2.status_code, 302)
        self.machine1.refresh_from_db()
        self.assertTrue(self.machine1.is_active)
