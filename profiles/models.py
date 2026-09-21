import uuid
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class Profile(models.Model):
    """Student profile — UUID PK, server-side privacy rules."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    university = models.CharField(max_length=200, blank=True)
    major = models.CharField(max_length=200, blank=True)
    year = models.CharField(max_length=50, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    city = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=40, blank=True)
    languages = models.CharField(max_length=300, blank=True)
    bio = models.TextField(blank=True, max_length=500)
    interests = models.CharField(max_length=300, blank=True)
    photo = models.ImageField(upload_to='profiles/', blank=True, null=True)
    is_public = models.BooleanField(default=True)
    questionnaire_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'profiles_profile'

    def __str__(self):
        return f"Profile for {self.user.email}"