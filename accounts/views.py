from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_POST
from django.db.models import Q
from .permissions import administrator_required, is_administrator, is_supervisor, is_engineer
from .forms import UserCreateForm, UserEditForm


class CustomLoginView(LoginView):
    """
    Custom LoginView for industrial station terminals.
    - Automatically redirects authenticated users away from the login form.
    - Honors the 'remember_me' station checkbox.
    - Preserves deep links ('next' parameter) and routes by role.
    """
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        remember_me = self.request.POST.get("remember_me")
        if not remember_me:
            self.request.session.set_expiry(0)
        else:
            self.request.session.set_expiry(1209600)
        return super().form_valid(form)

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to

        user = self.request.user

        if is_administrator(user):
            try:
                return reverse("admin_dashboard")
            except NoReverseMatch:
                pass
        elif is_supervisor(user):
            try:
                return reverse("supervisor_dashboard")
            except NoReverseMatch:
                pass
        elif is_engineer(user):
            try:
                return reverse("engineer_dashboard")
            except NoReverseMatch:
                pass

        return getattr(settings, "LOGIN_REDIRECT_URL", "/dashboard/")


@require_POST
def logout_view(request):
    """
    Terminates operator session via POST request.
    Appends a success message and redirects to the login terminal.
    """
    logout(request)
    messages.success(request, "Station terminal session terminated successfully.")
    return redirect("login")


# ============================================================================
# Administrator Operations: User Management & Role Assignment
# ============================================================================

@administrator_required
def user_list(request):
    """
    Administrator User Management Console.
    Lists all system users with role badges, status, and filtering.
    """
    query = request.GET.get("q", "").strip()
    role_filter = request.GET.get("role", "").strip()
    status_filter = request.GET.get("status", "").strip()

    users_qs = User.objects.prefetch_related("groups").order_by("-date_joined")

    if query:
        users_qs = users_qs.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )

    if role_filter:
        if role_filter == "Administrator":
            users_qs = users_qs.filter(Q(groups__name="Administrator") | Q(is_superuser=True)).distinct()
        elif role_filter in ["Supervisor", "Engineer"]:
            users_qs = users_qs.filter(groups__name=role_filter, is_superuser=False).distinct()

    if status_filter == "active":
        users_qs = users_qs.filter(is_active=True)
    elif status_filter == "inactive":
        users_qs = users_qs.filter(is_active=False)

    all_users = User.objects.prefetch_related("groups").all()
    total_users = all_users.count()
    active_users = all_users.filter(is_active=True).count()
    admin_count = all_users.filter(Q(groups__name="Administrator") | Q(is_superuser=True)).distinct().count()
    supervisor_count = all_users.filter(groups__name="Supervisor", is_superuser=False).distinct().count()
    engineer_count = all_users.filter(groups__name="Engineer", is_superuser=False).distinct().count()

    user_rows = []
    for user_obj in users_qs:
        roles = list(user_obj.groups.values_list("name", flat=True))
        if user_obj.is_superuser or "Administrator" in roles:
            assigned_role = "Administrator"
            role_badge = "badge-danger"
        elif "Supervisor" in roles:
            assigned_role = "Supervisor"
            role_badge = "badge-warning"
        elif "Engineer" in roles:
            assigned_role = "Engineer"
            role_badge = "badge-info"
        else:
            assigned_role = "Operator"
            role_badge = "badge-neutral"

        user_rows.append({
            "user": user_obj,
            "role": assigned_role,
            "role_badge": role_badge,
            "is_self": user_obj == request.user,
        })

    return render(
        request,
        "accounts/user_list.html",
        {
            "user_rows": user_rows,
            "total_users": total_users,
            "active_users": active_users,
            "admin_count": admin_count,
            "supervisor_count": supervisor_count,
            "engineer_count": engineer_count,
            "search_query": query,
            "role_filter": role_filter,
            "status_filter": status_filter,
        }
    )


@administrator_required
def user_create(request):
    """
    Administrator registers a new operator account and assigns role clearance.
    """
    if request.method == "POST":
        form = UserCreateForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            role = form.cleaned_data.get("role")
            messages.success(
                request,
                f"Operator account '{new_user.username}' created successfully with '{role}' clearance."
            )
            return redirect("user_list")
    else:
        form = UserCreateForm(initial={"is_active": True, "role": "Engineer"})

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "is_edit": False,
        }
    )


@administrator_required
def user_edit(request, user_id):
    """
    Administrator edits user credentials, active state, or role clearance.
    """
    target_user = get_object_or_404(User.objects.prefetch_related("groups"), pk=user_id)
    is_self = (target_user == request.user)

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=target_user)
        if form.is_valid():
            if is_self and not form.cleaned_data.get("is_active"):
                messages.error(request, "You cannot deactivate your own administrative account.")
                return redirect("user_edit", user_id=target_user.pk)

            updated_user = form.save()
            role = form.cleaned_data.get("role")
            messages.success(
                request,
                f"Account '{updated_user.username}' updated. Operational clearance set to '{role}'."
            )
            return redirect("user_list")
    else:
        form = UserEditForm(instance=target_user)

    return render(
        request,
        "accounts/user_form.html",
        {
            "form": form,
            "target_user": target_user,
            "is_edit": True,
            "is_self": is_self,
        }
    )


@administrator_required
@require_POST
def user_toggle_status(request, user_id):
    """
    Administrator quickly activates or deactivates an operator account.
    """
    target_user = get_object_or_404(User, pk=user_id)

    if target_user == request.user:
        messages.error(request, "You cannot deactivate your own active session.")
        return redirect("user_list")

    target_user.is_active = not target_user.is_active
    target_user.save(update_fields=["is_active"])

    status_str = "activated" if target_user.is_active else "deactivated"
    messages.success(request, f"User '{target_user.username}' has been {status_str}.")
    return redirect("user_list")
