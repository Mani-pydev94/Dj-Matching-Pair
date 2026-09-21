import uuid
from django.db import models
from django.conf import settings


class QuestionnaireCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('display_order', 'name')

    def __str__(self):
        return self.name


class Question(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category = models.CharField(max_length=100)
    question_key = models.CharField(max_length=100, unique=True, null=True, blank=True)
    category_ref = models.ForeignKey(
        QuestionnaireCategory, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='questions',
    )
    text = models.TextField()
    question_type = models.CharField(
        max_length=30,
        choices=[
            ('SINGLE_CHOICE', 'Single choice'),
            ('MULTIPLE_CHOICE', 'Multiple choice'),
            ('SCALE', 'Scale'),
            ('YES_NO', 'Yes/No'),
        ],
        default='SINGLE_CHOICE',
    )
    help_text = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    weight = models.FloatField(default=1.0)
    is_required = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['category', 'order']
        db_table = 'questionnaire_question'

    def __str__(self):
        return f"{self.category}: {self.text[:60]}"


class QuestionOption(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    option_text = models.CharField(max_length=255)
    option_value = models.CharField(max_length=100)
    display_order = models.PositiveIntegerField(default=0)
    compatibility_value = models.FloatField(default=1.0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ('display_order', 'id')
        constraints = [
            models.UniqueConstraint(
                fields=('question', 'option_value'),
                name='unique_question_option_value',
            ),
        ]


class QuestionResponse(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='question_responses')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='responses')
    value = models.CharField(max_length=500)
    selected_options = models.ManyToManyField(QuestionOption, blank=True, related_name='responses')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'question']
        db_table = 'questionnaire_response'

    def __str__(self):
        return f"{self.user.email} -> {self.question.category}: {self.value}"