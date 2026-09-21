from django.conf import settings
from django.db import models


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start = models.DateTimeField()
    location = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=7, default='#7C4DFF')
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='events',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('start',)

    def __str__(self):
        return self.title


class EventRegistration(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='event_registrations')
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=30)
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-registered_at',)
        constraints = [
            models.UniqueConstraint(
                fields=('event', 'user'),
                name='unique_event_registration',
            ),
        ]

    def __str__(self):
        return f'{self.name} - {self.event.title}'
