from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from connections.models import Connection
from .models import Message


class ChatTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='chat-a@example.com', password='Strong-password-123')
        self.other = User.objects.create_user(email='chat-b@example.com', password='Strong-password-123')
        self.client.force_login(self.user)

    def test_chat_requires_accepted_connection(self):
        response = self.client.get(reverse('chat_conversation', args=[self.other.id]))
        self.assertEqual(response.status_code, 404)
        response = self.client.post(
            reverse('chat_send_message', args=[self.other.id]),
            {'content': 'Hello'},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Message.objects.count(), 0)

    def test_connected_users_can_open_and_send_messages(self):
        Connection.objects.create(requester=self.user, recipient=self.other, status='ACCEPTED')
        response = self.client.post(
            reverse('chat_conversation', args=[self.other.id]),
            {'content': 'Hello there'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Message.objects.filter(sender=self.user, recipient=self.other).exists())

    def test_unread_count_returns_messages_for_current_user(self):
        Connection.objects.create(requester=self.user, recipient=self.other, status='ACCEPTED')
        Message.objects.create(sender=self.other, recipient=self.user, content='Unread')
        Message.objects.create(
            sender=self.other,
            recipient=self.user,
            content='Read',
            is_read=True,
        )

        response = self.client.get(reverse('chat_unread_count'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'unread_count': 1})
