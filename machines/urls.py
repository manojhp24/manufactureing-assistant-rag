from django.urls import path
from . import views

urlpatterns = [
    path("", views.machine_list, name="machine_list"),
    path("create/", views.machine_create, name="machine_create"),
    path("<int:pk>/edit/", views.machine_edit, name="machine_edit"),
    path("<int:pk>/toggle-status/", views.machine_toggle_status, name="machine_toggle_status"),
]
