import re
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import SignupOTP, User
from profiles.models import Profile


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class SignupEmailOTPTests(TestCase):
    def setUp(self):
        mail.outbox = []
        self.signup_data = {
            'full_name': 'Test Student',
            'email': 'student@example.com',
            'password1': 'Strong-password-123!',
            'password2': 'Strong-password-123!',
            'terms': 'on',
        }

    def create_pending_signup(self):
        response = self.client.post(reverse('signup'), self.signup_data)
        self.assertRedirects(response, reverse('verify_signup_email'))
        self.user = User.objects.get(email='student@example.com')
        self.otp = SignupOTP.objects.get(user=self.user)
        self.code = re.search(r'code is ([A-Z0-9]{6})', mail.outbox[-1].body).group(1)

    def test_signup_sends_mixed_uppercase_alphanumeric_code_and_blocks_login(self):
        response = self.client.post(reverse('signup'), self.signup_data)

        self.assertRedirects(response, reverse('verify_signup_email'))
        user = User.objects.get(email='student@example.com')
        code = re.search(r'code is ([A-Z0-9]{6})', mail.outbox[0].body).group(1)
        self.assertEqual(len(code), 6)
        self.assertRegex(code, r'[A-Z]')
        self.assertRegex(code, r'[0-9]')
        self.assertFalse(user.is_active)
        self.assertFalse(user.is_verified)
        self.assertTrue(Profile.objects.filter(user=user).exists())
        self.assertFalse(self.client.session.get('_auth_user_id'))

        login_response = self.client.post(reverse('login'), {
            'username': user.email,
            'password': self.signup_data['password1'],
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertFalse(self.client.session.get('_auth_user_id'))

    def test_valid_code_verifies_once_activates_and_logs_in(self):
        self.create_pending_signup()

        response = self.client.post(reverse('verify_signup_email'), {'code': self.code.lower()})

        self.assertRedirects(response, reverse('profiles:profile_setup'))
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertTrue(self.user.is_verified)
        self.assertTrue(self.client.session.get('_auth_user_id'))
        self.assertFalse(SignupOTP.objects.filter(user=self.user).exists())
        self.assertFalse(self.client.session.get('pending_signup_user_id'))

    def test_invalid_attempts_are_limited_and_correct_code_is_rejected_after_limit(self):
        self.create_pending_signup()

        for attempt in range(5):
            response = self.client.post(reverse('verify_signup_email'), {'code': 'ZZZZZ9'})
        self.assertContains(response, 'Too many incorrect attempts')
        self.assertEqual(SignupOTP.objects.get(user=self.user).attempts, 5)

        response = self.client.post(reverse('verify_signup_email'), {'code': self.code})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.user.is_active)
        self.assertFalse(self.user.is_verified)

    def test_expired_code_cannot_verify_but_can_be_resent(self):
        self.create_pending_signup()
        SignupOTP.objects.filter(user=self.user).update(expires_at=timezone.now() - timedelta(seconds=1))

        response = self.client.post(reverse('verify_signup_email'), {'code': self.code})

        self.assertContains(response, 'This code has expired')
        self.assertFalse(self.user.is_active)

        SignupOTP.objects.filter(user=self.user).update(last_sent_at=timezone.now() - timedelta(minutes=2))
        response = self.client.post(reverse('resend_signup_otp'))

        self.assertRedirects(response, reverse('verify_signup_email'))
        self.assertEqual(len(mail.outbox), 2)
        refreshed_otp = SignupOTP.objects.get(user=self.user)
        self.assertGreater(refreshed_otp.expires_at, timezone.now())
        self.assertEqual(refreshed_otp.attempts, 0)

    def test_resend_cooldown_and_email_delivery_failure_are_handled(self):
        self.create_pending_signup()

        response = self.client.post(reverse('resend_signup_otp'), follow=True)

        self.assertContains(response, 'Please wait')
        self.assertEqual(len(mail.outbox), 1)

    @patch('accounts.views.send_mail', return_value=0)
    def test_failed_email_delivery_does_not_create_pending_account(self, send_mail_mock):
        response = self.client.post(reverse('signup'), self.signup_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'We could not send your verification email')
        self.assertFalse(User.objects.filter(email='student@example.com').exists())
        send_mail_mock.assert_called_once()

    def test_allauth_email_signup_redirects_to_otp_signup_flow(self):
        response = self.client.get('/accounts/signup/')

        self.assertRedirects(response, reverse('signup'))
