from django.urls import path
from . import views

urlpatterns = [
    path("chat/", views.chat_view, name="assistant_chat"),
    path("ask/", views.chat_view, name="ask_question"),
    path("history/", views.history_view, name="assistant_history"),
    path("answer/<int:pk>/", views.answer_detail_view, name="answer_detail"),
    path("supervisor/history/", views.supervisor_history_view, name="supervisor_history"),
]
