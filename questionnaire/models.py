import uuid
from django.db import models
from django.conf import settings


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=100)
    text = models.TextField()
    order = models.PositiveIntegerField(default=0)
    weight = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'order']
        db_table = 'questionnaire_question'

    def __str__(self):
        return f"{self.category}: {self.text[:60]}"


class QuestionResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='question_responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    value = models.CharField(max_length=500)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'question']
        db_table = 'questionnaire_response'

    def __str__(self):
        return f"{self.user.email} -> {self.question.category}: {self.value}"