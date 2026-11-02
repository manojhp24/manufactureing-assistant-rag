"""
Context processors for the accounts app.
Exposes role verification flags and role labels to all Django templates.
"""
from .permissions import get_user_roles, is_administrator, is_supervisor, is_engineer


def user_roles(request):
    """
    Supplies convenient role context variables to all templates.
    Avoids expensive database lookups and brittle string formatting in templates.
    """
    user = getattr(request, "user", None)

    if not user or not user.is_authenticated:
        return {
            "is_admin": False,
            "is_supervisor": False,
            "is_engineer": False,
            "user_role": None,
            "user_role_label": "Guest",
        }

    admin = is_administrator(user)
    roles = get_user_roles(user)

    # Specific role assignments for UI labeling
    if admin or user.is_superuser:
        role_slug = "administrator"
        label = "Admin"
    elif "Supervisor" in roles:
        role_slug = "supervisor"
        label = "Supervisor"
    elif "Engineer" in roles:
        role_slug = "engineer"
        label = "Engineer"
    else:
        role_slug = "operator"
        label = "Operator"

    return {
        "is_admin": admin,
        "is_supervisor": is_supervisor(user),
        "is_engineer": is_engineer(user),
        "user_role": role_slug,
        "user_role_label": label,
    }

