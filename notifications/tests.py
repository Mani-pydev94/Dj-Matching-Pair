from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from connections.models import Connection
from .models import Notification


class NotificationAPITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='recipient@example.com', password='Strong-password-123')
        self.sender = User.objects.create_user(email='sender@example.com', password='Strong-password-123')
        self.connection = Connection.objects.create(
            requester=self.sender, recipient=self.user, status='PENDING')
        self.notification = Notification.objects.create(
            user=self.user, title='New connection request', message='Connect', connection=self.connection)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_unread_list_and_mark_read(self):
        response = self.client.get('/notifications/')
        self.assertEqual(response.data['unread_count'], 1)
        self.assertEqual(response.data['results'][0]['connection_id'], str(self.connection.id))
        response = self.client.get('/notifications/unread-count/')
        self.assertEqual(response.data['unread_count'], 1)
        response = self.client.post(f'/notifications/{self.notification.id}/read/')
        self.assertTrue(response.data['is_read'])
        self.assertEqual(self.client.get('/notifications/unread-count/').data['unread_count'], 0)

    def test_accept_from_notification_updates_connection(self):
        response = self.client.post(f'/notifications/{self.notification.id}/accept/')
        self.assertEqual(response.data['status'], 'ACCEPTED')
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, 'ACCEPTED')
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    def test_request_creates_recipient_notification(self):
        self.connection.delete()
        self.notification.delete()
        self.client.force_authenticate(self.sender)
        response = self.client.post('/api/connections/request/', {'user_id': str(self.user.id)}, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Notification.objects.filter(
            user=self.user, title='New connection request',
        ).exists())

    def test_requester_can_cancel_pending_request(self):
        self.client.force_authenticate(self.sender)
        response = self.client.post(f'/api/connections/{self.connection.id}/cancel/')
        self.assertEqual(response.status_code, 200)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, 'DECLINED')

    def test_either_connected_user_can_cancel_connection(self):
        self.connection.status = 'ACCEPTED'
        self.connection.save(update_fields=('status',))
        self.client.force_authenticate(self.user)
        response = self.client.post(f'/api/connections/{self.connection.id}/cancel/')
        self.assertEqual(response.status_code, 200)
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, 'DECLINED')
        self.assertTrue(Notification.objects.filter(
            user=self.sender, title='Connection cancelled',
        ).exists())
