"""
Unit tests for the accounts application.
Covers RBAC functions, decorators, CBV mixins, views, sessions, and context processors.
"""
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, Group, AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.urls import reverse
from django.views import View

from accounts.permissions import (
    is_administrator,
    is_engineer,
    is_supervisor,
    administrator_required,
    engineer_required,
    supervisor_required,
    AdministratorRequiredMixin,
    EngineerRequiredMixin,
    SupervisorRequiredMixin,
)
from accounts.context_processors import user_roles


class AccountsRBACTests(TestCase):
    def setUp(self):
        self.admin_group, _ = Group.objects.get_or_create(name="Administrator")
        self.engineer_group, _ = Group.objects.get_or_create(name="Engineer")
        self.supervisor_group, _ = Group.objects.get_or_create(name="Supervisor")

        # Superuser
        self.superuser = User.objects.create_superuser(
            username="super_root", password="password123", email="root@plant.local"
        )
        # Administrator
        self.admin_user = User.objects.create_user(
            username="plant_admin", password="password123"
        )
        self.admin_user.groups.add(self.admin_group)

        # Engineer
        self.engineer_user = User.objects.create_user(
            username="field_eng", password="password123"
        )
        self.engineer_user.groups.add(self.engineer_group)

        # Supervisor
        self.supervisor_user = User.objects.create_user(
            username="shift_sup", password="password123"
        )
        self.supervisor_user.groups.add(self.supervisor_group)

        # Plain user without group
        self.plain_user = User.objects.create_user(
            username="unassigned_op", password="password123"
        )

        self.factory = RequestFactory()

    def test_anonymous_user_denied_all(self):
        anon = AnonymousUser()
        self.assertFalse(is_administrator(anon))
        self.assertFalse(is_engineer(anon))
        self.assertFalse(is_supervisor(anon))

    def test_superuser_has_all_privileges(self):
        self.assertTrue(is_administrator(self.superuser))
        self.assertTrue(is_engineer(self.superuser))
        self.assertTrue(is_supervisor(self.superuser))

    def test_admin_has_admin_and_subordinate_privileges(self):
        self.assertTrue(is_administrator(self.admin_user))
        self.assertTrue(is_engineer(self.admin_user))
        self.assertTrue(is_supervisor(self.admin_user))

    def test_engineer_privileges(self):
        self.assertFalse(is_administrator(self.engineer_user))
        self.assertTrue(is_engineer(self.engineer_user))
        self.assertFalse(is_supervisor(self.engineer_user))

    def test_supervisor_privileges(self):
        self.assertFalse(is_administrator(self.supervisor_user))
        self.assertTrue(is_engineer(self.supervisor_user))
        self.assertTrue(is_supervisor(self.supervisor_user))

    def test_unassigned_user_privileges(self):
        self.assertFalse(is_administrator(self.plain_user))
        self.assertFalse(is_engineer(self.plain_user))
        self.assertFalse(is_supervisor(self.plain_user))

    def test_role_caching(self):
        # Trigger cache
        roles = accounts_roles = is_administrator(self.admin_user)
        self.assertTrue(hasattr(self.admin_user, "_cached_roles"))
        self.assertIn("Administrator", self.admin_user._cached_roles)

    def test_decorator_redirects_unauthenticated_user(self):
        @administrator_required
        def dummy_view(request):
            return HttpResponse("OK")

        req = self.factory.get("/manuals/upload/")
        req.user = AnonymousUser()
        response = dummy_view(req)

        self.assertEqual(response.status_code, 302)
        self.assertIn("login?next=/manuals/upload/", response.url)

    def test_decorator_raises_403_for_authenticated_unauthorized_user(self):
        @administrator_required
        def dummy_view(request):
            return HttpResponse("OK")

        req = self.factory.get("/manuals/upload/")
        req.user = self.engineer_user

        # Must raise PermissionDenied instead of redirect loop
        with self.assertRaises(PermissionDenied):
            dummy_view(req)

    def test_decorator_allows_authorized_user(self):
        @administrator_required
        def dummy_view(request):
            return HttpResponse("ACCESS_GRANTED")

        req = self.factory.get("/manuals/upload/")
        req.user = self.admin_user
        response = dummy_view(req)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "ACCESS_GRANTED")

    def test_cbv_mixin_raises_403_for_unauthorized(self):
        class ProtectedView(AdministratorRequiredMixin, View):
            def get(self, request):
                return HttpResponse("CBV_OK")

        req = self.factory.get("/manuals/upload/")
        req.user = self.engineer_user

        with self.assertRaises(PermissionDenied):
            ProtectedView.as_view()(req)

    def test_cbv_mixin_allows_authorized(self):
        class ProtectedView(AdministratorRequiredMixin, View):
            def get(self, request):
                return HttpResponse("CBV_OK")

        req = self.factory.get("/manuals/upload/")
        req.user = self.admin_user
        res = ProtectedView.as_view()(req)
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.content.decode(), "CBV_OK")


class AccountsViewsAndAuthTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_group, _ = Group.objects.get_or_create(name="Administrator")
        self.admin_user = User.objects.create_user(
            username="plant_admin", password="password123"
        )
        self.admin_user.groups.add(self.admin_group)

    def test_accounts_home_redirects_to_login(self):
        response = self.client.get("/accounts/")
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

    def test_login_page_renders_cleanly(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_success_with_remember_me(self):
        response = self.client.post(
            reverse("login"),
            {"username": "plant_admin", "password": "password123", "remember_me": "on"},
        )
        self.assertEqual(response.status_code, 302)
        # Session expiry should be persistent
        self.assertEqual(self.client.session.get_expiry_age(), 1209600)

    def test_login_success_without_remember_me(self):
        response = self.client.post(
            reverse("login"),
            {"username": "plant_admin", "password": "password123"},
        )
        self.assertEqual(response.status_code, 302)
        # Session should expire at browser close
        self.assertTrue(self.client.session.get_expire_at_browser_close())

    def test_login_preserves_next_parameter(self):
        target_path = "/manuals/list/"
        response = self.client.post(
            f"{reverse('login')}?next={target_path}",
            {"username": "plant_admin", "password": "password123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, target_path)

    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username="plant_admin", password="password123")
        response = self.client.get(reverse("login"))
        # Should redirect away because redirect_authenticated_user = True
        self.assertEqual(response.status_code, 302)

    def test_logout_get_method_rejected(self):
        self.client.login(username="plant_admin", password="password123")
        response = self.client.get(reverse("logout"))
        # LogoutView is @require_POST
        self.assertEqual(response.status_code, 405)

    def test_logout_post_success(self):
        self.client.login(username="plant_admin", password="password123")
        response = self.client.post(reverse("logout"))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("login"))

        # Verify session is flushed
        response_dash = self.client.get(reverse("login"))
        self.assertContains(response_dash, "Station terminal session terminated successfully.")


class AccountsContextProcessorTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.admin_group, _ = Group.objects.get_or_create(name="Administrator")
        self.engineer_group, _ = Group.objects.get_or_create(name="Engineer")

        self.admin_user = User.objects.create_user(
            username="admin_test", password="password123"
        )
        self.admin_user.groups.add(self.admin_group)

        self.engineer_user = User.objects.create_user(
            username="eng_test", password="password123"
        )
        self.engineer_user.groups.add(self.engineer_group)

    def test_anonymous_context(self):
        req = self.factory.get("/")
        req.user = AnonymousUser()
        ctx = user_roles(req)
        self.assertFalse(ctx["is_admin"])
        self.assertFalse(ctx["is_engineer"])
        self.assertIsNone(ctx["user_role"])
        self.assertEqual(ctx["user_role_label"], "Guest")

    def test_admin_context(self):
        req = self.factory.get("/")
        req.user = self.admin_user
        ctx = user_roles(req)
        self.assertTrue(ctx["is_admin"])
        self.assertEqual(ctx["user_role"], "administrator")
        self.assertEqual(ctx["user_role_label"], "Admin")

    def test_engineer_context(self):
        req = self.factory.get("/")
        req.user = self.engineer_user
        ctx = user_roles(req)
        self.assertFalse(ctx["is_admin"])
        self.assertTrue(ctx["is_engineer"])
        self.assertEqual(ctx["user_role"], "engineer")
        self.assertEqual(ctx["user_role_label"], "Engineer")
