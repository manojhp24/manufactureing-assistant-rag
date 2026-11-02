from django.db import models
from django.contrib.auth.models import User
from machines.models import Machine


class QuestionAnswer(models.Model):

    class Status(models.TextChoices):
        ANSWERED = "answered", "Answered"
        INSUFFICIENT = "insufficient", "Insufficient Information"
        CONFLICTING = "conflicting", "Conflicting Information"

    engineer = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    machine = models.ForeignKey(
        Machine,
        on_delete=models.CASCADE,
        related_name="questions"
    )

    question = models.TextField()
    answer = models.TextField(blank=True)

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.INSUFFICIENT
    )

    citations = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.machine.model_number}: {self.question[:60]}"

    @property
    def answer_status(self):
        return self.status

    @property
    def answered_at(self):
        return self.created_at

    @property
    def user(self):
        return self.engineer
