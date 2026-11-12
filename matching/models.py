import uuid
from django.db import models
from django.conf import settings


class Match(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='matches_from')
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='matches_to')
    compatibility_score = models.FloatField(default=0.0)
    status = models.CharField(max_length=20, default='PENDING', choices=[
        ('PENDING', 'Pending'), ('ACCEPTED', 'Accepted'), ('DECLINED', 'Declined'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_match'
        unique_together = [['user_a', 'user_b']]


class CompatibilityStory(models.Model):
    """Cached AI-written 'Why You Two Click' story for a connection pair.

    Keyed on the canonical, order-independent pair fingerprint so a story
    is generated once and shared whichever student is viewing the page.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_a = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='click_stories_a')
    user_b = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='click_stories_b')
    story = models.JSONField(default=dict)
    pair_fingerprint = models.CharField(max_length=128, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'matching_compatibility_story'


class MatchInsight(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.OneToOneField(Match, on_delete=models.CASCADE, related_name='insight')
    insight_text = models.TextField()
    is_ai_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)