import uuid
from django.db import models
from django.conf import settings


CONNECTION_STATUS = [
    ('NONE', 'None'),
    ('PENDING', 'Pending'),
    ('ACCEPTED', 'Accepted'),
    ('DECLINED', 'Declined'),
    ('BLOCKED', 'Blocked'),
    ('CONNECTED', 'Connected'),
]

class Connection(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_requests')
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_requests')
    status = models.CharField(max_length=20, choices=CONNECTION_STATUS, default='NONE')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'connections_connection'
        unique_together = [['requester', 'recipient']]

    def __str__(self):
        return f"{self.requester.email} -> {self.recipient.email} ({self.status})"