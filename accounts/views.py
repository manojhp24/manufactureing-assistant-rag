from django.contrib.auth.views import LoginView
from django.contrib.auth import logout
from django.contrib import messages
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_POST
from .permissions import is_administrator, is_supervisor, is_engineer


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
        # Handle 'remember_me' from login template
        remember_me = self.request.POST.get("remember_me")
        if not remember_me:
            # Session expires when user closes their browser
            self.request.session.set_expiry(0)
        else:
            # Retain session for 2 weeks (or configured default)
            self.request.session.set_expiry(1209600)

        return super().form_valid(form)

    def get_success_url(self):
        # 1. Prioritize explicit next parameter if safe
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to

        user = self.request.user

        # 2. Smart role-based dashboard dispatching
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

        # 3. Fallback to settings or default
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
