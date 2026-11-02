from django.urls import path
from . import views

urlpatterns = [
    path("", views.manual_list, name="manual_list"),
    path("upload/", views.upload_manual, name="upload_manual"),
]