from io import BytesIO
import tempfile

from PIL import Image
from django.core.files.uploadedfile import SimpleUploadedFile
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
        response = self.client.get(reverse('chat_messages', args=[self.other.id]))
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

    def test_connected_users_can_send_and_receive_photo_messages(self):
        Connection.objects.create(requester=self.user, recipient=self.other, status='ACCEPTED')
        image_data = BytesIO()
        Image.new('RGB', (2, 2), color='purple').save(image_data, format='PNG')
        upload = SimpleUploadedFile('campus.png', image_data.getvalue(), content_type='image/png')

        with tempfile.TemporaryDirectory() as media_root, self.settings(MEDIA_ROOT=media_root):
            response = self.client.post(
                reverse('chat_send_message', args=[self.other.id]),
                {'content': 'Campus day!', 'image': upload},
            )

            self.assertEqual(response.status_code, 200)
            self.assertIn(reverse('chat_message_image', args=[response.json()['id']]), response.json()['image_url'])
            message = Message.objects.get(sender=self.user, recipient=self.other)
            self.assertTrue(message.image)

            self.client.force_login(self.other)
            response = self.client.get(reverse('chat_messages', args=[self.user.id]))
            self.assertEqual(response.status_code, 200)
            image_url = response.json()['messages'][0]['image_url']
            self.assertIn(reverse('chat_message_image', args=[message.id]), image_url)
            image_response = self.client.get(image_url)
            self.assertEqual(image_response.status_code, 200)
            image_response.close()

            outsider = User.objects.create_user(email='outsider@example.com', password='Strong-password-123')
            self.client.force_login(outsider)
            self.assertEqual(self.client.get(image_url).status_code, 404)

    def test_chat_rejects_invalid_photo_upload(self):
        Connection.objects.create(requester=self.user, recipient=self.other, status='ACCEPTED')
        upload = SimpleUploadedFile('not-an-image.png', b'not image data', content_type='image/png')

        response = self.client.post(
            reverse('chat_send_message', args=[self.other.id]),
            {'image': upload},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Message.objects.count(), 0)

    def test_conversation_updates_return_messages_after_cursor(self):
        Connection.objects.create(requester=self.user, recipient=self.other, status='ACCEPTED')
        first = Message.objects.create(
            sender=self.other,
            recipient=self.user,
            content='First message',
        )
        response = self.client.get(reverse('chat_messages', args=[self.other.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [message['content'] for message in response.json()['messages']],
            ['First message'],
        )
        self.assertTrue(Message.objects.get(id=first.id).is_read)

        Message.objects.create(sender=self.other, recipient=self.user, content='Live update')
        response = self.client.get(
            reverse('chat_messages', args=[self.other.id]),
            {'after': str(first.id)},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [message['content'] for message in response.json()['messages']],
            ['Live update'],
        )
        self.assertFalse(response.json()['messages'][0]['is_mine'])

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

    def test_chat_home_shows_recent_message_and_unread_count(self):
        Connection.objects.create(requester=self.user, recipient=self.other, status='ACCEPTED')
        Message.objects.create(sender=self.other, recipient=self.user, content='See you at the library')

        response = self.client.get(reverse('chat_home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Messages')
        self.assertContains(response, 'See you at the library')
        self.assertContains(response, '1 unread')
        self.assertContains(response, 'Unread')
