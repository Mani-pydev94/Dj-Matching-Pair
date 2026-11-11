from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .forms import EventAdminForm, EventRegistrationForm
from .models import Event, EventRegistration


def make_user(email):
    return User.objects.create_user(email=email, password='testpass123')


class EventFormTests(TestCase):
    def test_admin_form_rejects_invalid_hex_color(self):
        form = EventAdminForm(
            {
                'title': 'Rave',
                'description': '',
                'start': '2026-12-01T19:00',
                'location': 'Main Hall',
                'color': 'red',
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn('color', form.errors)

    def test_admin_form_accepts_valid_hex_color(self):
        form = EventAdminForm(
            {
                'title': 'Rave',
                'description': '',
                'start': '2026-12-01T19:00',
                'location': 'Main Hall',
                'color': '#123ABC',
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_registration_form_requires_at_least_seven_phone_digits(self):
        form = EventRegistrationForm(
            {'name': 'Ali', 'email': 'ali@example.com', 'phone_number': '12345'}
        )
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)

    def test_registration_form_accepts_phone_with_spaces_or_symbols(self):
        form = EventRegistrationForm(
            {'name': 'Ali', 'email': 'ali@example.com', 'phone_number': '+91 98765-43210'}
        )
        self.assertTrue(form.is_valid(), form.errors)


class EventViewTests(TestCase):
    def setUp(self):
        self.user = make_user('events-user@example.com')
        self.client.force_login(self.user)
        self.event = Event.objects.create(title='Neon Night', start='2026-12-05T19:00:00Z')

    def test_home_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('events_home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_home_lists_events(self):
        response = self.client.get(reverse('events_home'))
        self.assertContains(response, 'Neon Night')

    def test_detail_404s_for_unknown_event(self):
        response = self.client.get(reverse('event_detail', args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_register_is_post_only(self):
        response = self.client.get(reverse('register_event', args=[self.event.id]))
        self.assertEqual(response.status_code, 405)

    def test_register_creates_registration_and_notification(self):
        from notifications.models import Notification

        response = self.client.post(
            reverse('register_event', args=[self.event.id]),
            {'name': 'Ali', 'email': 'ali@example.com', 'phone_number': '+91 9876543210'},
        )
        self.assertEqual(response.status_code, 302)
        registration = EventRegistration.objects.get(event=self.event, user=self.user)
        self.assertEqual(registration.name, 'Ali')
        self.assertIn(self.user, self.event.attendees.all())
        self.assertTrue(
            Notification.objects.filter(
                user=self.user, title='Event registration successful'
            ).exists()
        )

    def test_double_register_is_blocked_with_info_message(self):
        EventRegistration.objects.create(
            event=self.event, user=self.user, name='Ali', email='ali@example.com',
            phone_number='+91 9876543210',
        )
        response = self.client.post(
            reverse('register_event', args=[self.event.id]),
            {'name': 'Ali', 'email': 'ali@example.com', 'phone_number': '+91 9876543210'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(EventRegistration.objects.filter(event=self.event, user=self.user).count(), 1)
        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(any('already registered' in m for m in messages), messages)

    def test_register_rejects_invalid_form_data(self):
        response = self.client.post(
            reverse('register_event', args=[self.event.id]),
            {'name': '', 'email': 'not-an-email', 'phone_number': '12'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(
            EventRegistration.objects.filter(event=self.event, user=self.user).exists()
        )
