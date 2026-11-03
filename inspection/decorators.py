from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def supervisor_required(view_func):

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        is_supervisor = request.user.groups.filter(
            name="Supervisor"
        ).exists()

        if not (is_supervisor or request.user.is_superuser):
            raise PermissionDenied(
                "Only supervisors can review inspections."
            )

        return view_func(request, *args, **kwargs)

    return wrapper