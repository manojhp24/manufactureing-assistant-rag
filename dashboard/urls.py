
from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard_home, name="dashboard"),
    path("admin/", views.admin_dashboard, name="admin_dashboard"),
    path("engineer/", views.engineer_dashboard, name="engineer_dashboard"),
    path("supervisor/", views.supervisor_dashboard, name="supervisor_dashboard"),
]
