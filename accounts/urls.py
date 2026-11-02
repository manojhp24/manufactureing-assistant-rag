from django.urls import path
from django.views.generic import RedirectView
from .views import CustomLoginView, logout_view

urlpatterns = [
    path(
        "",
        RedirectView.as_view(pattern_name="login", permanent=False),
        name="accounts_home",
    ),
    path(
        "login/",
        CustomLoginView.as_view(),
        name="login",
    ),
    path(
        "logout/",
        logout_view,
        name="logout",
    ),
]
