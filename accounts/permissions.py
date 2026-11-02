"""
Role-based access control (RBAC) permissions for Manufacturing Manuals RAG.
Provides role testing utilities, view decorators, and Class-Based View (CBV) mixins.
"""
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib.auth.mixins import AccessMixin


def get_user_roles(user):
    """
    Return a cached set of group names for the user on this request.
    Avoids repetitive SQL queries when multiple permission checks occur.
    """
    if not user.is_authenticated:
        return set()
    if not hasattr(user, "_cached_roles"):
        user._cached_roles = set(user.groups.values_list("name", flat=True))
    return user._cached_roles


def is_administrator(user):
    """
    Check if the user has Administrator privileges.
    Superusers automatically qualify as administrators.
    """
    return user.is_authenticated and (
        user.is_superuser or "Administrator" in get_user_roles(user)
    )


def is_supervisor(user):
    """
    Check if the user has Supervisor privileges.
    Administrators and Superusers also hold supervisor clearance.
    """
    return user.is_authenticated and (
        user.is_superuser
        or "Supervisor" in get_user_roles(user)
        or "Administrator" in get_user_roles(user)
    )


def is_engineer(user):
    """
    Check if the user has Engineer privileges.
    Administrators, Supervisors, and Superusers also hold engineering clearance.
    """
    return user.is_authenticated and (
        user.is_superuser
        or "Engineer" in get_user_roles(user)
        or "Supervisor" in get_user_roles(user)
        or "Administrator" in get_user_roles(user)
    )


def role_required(role_test_func, login_url="login"):
    """
    Decorator for views that checks that the user passes the given role test.
    - If the user is not authenticated, redirects to `login_url` preserving the `next` path.
    - If the user is authenticated but lacks required role, raises PermissionDenied (HTTP 403),
      preventing silent redirect bounce loops.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"{login_url}?next={request.path}")
            if not role_test_func(request.user):
                raise PermissionDenied(
                    "Access denied: you do not possess the required terminal clearance for this operation."
                )
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


administrator_required = role_required(is_administrator)
engineer_required = role_required(is_engineer)
supervisor_required = role_required(is_supervisor)


# Class-Based View Mixins
class RoleRequiredMixin(AccessMixin):
    """
    Base CBV mixin that enforces a role test function.
    Raises PermissionDenied for authenticated users lacking privileges.
    """
    role_test_func = staticmethod(lambda u: True)

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not self.role_test_func(request.user):
            raise PermissionDenied(
                "Access denied: you do not possess the required terminal clearance for this operation."
            )
        return super().dispatch(request, *args, **kwargs)


class AdministratorRequiredMixin(RoleRequiredMixin):
    role_test_func = staticmethod(is_administrator)


class EngineerRequiredMixin(RoleRequiredMixin):
    role_test_func = staticmethod(is_engineer)


class SupervisorRequiredMixin(RoleRequiredMixin):
    role_test_func = staticmethod(is_supervisor)
