from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    path(
        "",
        RedirectView.as_view(pattern_name="login", permanent=False),
        name="accounts_home",
    ),
    path(
        "login/",
        views.CustomLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),

    # Administrator User Management Operations (Admin Only)
    path(
        "users/",
        views.user_list,
        name="user_list",
    ),
    path(
        "users/create/",
        views.user_create,
        name="user_create",
    ),
    path(
        "users/<int:user_id>/edit/",
        views.user_edit,
        name="user_edit",
    ),
    path(
        "users/<int:user_id>/toggle/",
        views.user_toggle_status,
        name="user_toggle",
    ),
]
