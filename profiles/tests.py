from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image
from rest_framework.test import APIClient

from accounts.models import User
from .models import Profile
from connections.models import Connection


class ProfileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='owner@example.com',
            password='Strong-password-123',
            first_name='Owner',
            last_name='Student',
        )
        self.other = User.objects.create_user(
            email='other@example.com',
            password='Strong-password-123',
            first_name='Other',
            last_name='Student',
        )
        Profile.objects.create(user=self.user, is_public=True)
        Profile.objects.create(user=self.other, is_public=False)

    def image_upload(self, content_type='image/png'):
        output = BytesIO()
        Image.new('RGB', (20, 20), color='purple').save(output, format='PNG')
        return SimpleUploadedFile('avatar.png', output.getvalue(), content_type=content_type)

    def test_unauthenticated_profile_is_rejected(self):
        response = self.client.get('/api/profile/me/')
        self.assertEqual(response.status_code, 403)

    def test_get_and_patch_own_profile(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/profile/me/')
        self.assertEqual(response.status_code, 200)
        response = self.client.patch('/api/profile/me/', {'city': 'Hyderabad', 'gender': 'Male'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['city'], 'Hyderabad')
        self.assertEqual(response.data['gender'], 'Male')

    def test_partial_update_does_not_clear_other_fields(self):
        profile = self.user.profile
        profile.city = 'Hyderabad'
        profile.bio = 'Student bio'
        profile.save()
        self.client.force_authenticate(self.user)
        response = self.client.patch('/api/profile/me/', {'city': 'Bengaluru'}, format='json')
        self.assertEqual(response.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.city, 'Bengaluru')
        self.assertEqual(profile.bio, 'Student bio')

    def test_photo_upload_and_invalid_image_rejected(self):
        self.client.force_authenticate(self.user)
        response = self.client.patch(
            '/api/profile/me/photo/',
            {'photo': self.image_upload()},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['profile_photo'])
        response = self.client.patch(
            '/api/profile/me/photo/',
            {'photo': SimpleUploadedFile('bad.png', b'not-an-image', content_type='image/png')},
            format='multipart',
        )
        self.assertEqual(response.status_code, 400)

    def test_profile_strength_is_database_derived(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/profile/me/strength/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['profile_strength'], 0)
        self.user.profile.bio = 'A real bio'
        self.user.profile.save()
        response = self.client.get('/api/profile/me/strength/')
        self.assertEqual(response.data['profile_strength'], 10)

    def test_private_public_profile_is_forbidden(self):
        self.client.force_authenticate(self.user)
        response = self.client.get(f'/api/students/{self.other.id}/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.data.keys()), {'id', 'display_name'})
        self.other.profile.is_public = True
        self.other.profile.save()
        response = self.client.get(f'/api/students/{self.other.id}/profile/')
        self.assertEqual(response.status_code, 200)

    def test_stats_return_real_zero_values(self):
        self.client.force_authenticate(self.user)
        response = self.client.get('/api/profile/me/stats/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['communities_count'], 0)
        self.assertEqual(response.data['chats_count'], 0)
        self.assertEqual(response.data['events_count'], 0)
        self.assertEqual(response.data['answers_count'], 0)

    def test_public_profile_preview_hides_photo_until_accepted(self):
        self.other.profile.is_public = True
        self.other.profile.bio = 'Private bio'
        self.other.profile.interests = 'Chess'
        self.other.profile.save()
        self.client.force_authenticate(self.user)
        response = self.client.get(f'/api/students/{self.other.id}/profile/')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('bio', response.data)
        self.assertNotIn('profile_photo', response.data)
        Connection.objects.create(requester=self.user, recipient=self.other, status='ACCEPTED')
        response = self.client.get(f'/api/students/{self.other.id}/profile/')
        self.assertIn('bio', response.data)


class ProfileSetupTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='setup@example.com',
            password='Strong-password-123',
            first_name='Setup',
            last_name='Student',
        )
        Profile.objects.create(user=self.user)
        self.client.force_login(self.user)

    def test_initial_academic_profile_is_discoverable(self):
        response = self.client.post(reverse('profiles:profile_setup'), {
            'display_name': 'Setup Student',
            'university': 'Campus University',
            'city': 'Bengaluru',
            'major': 'Computer Science',
            'year': '3rd Year',
        })
        self.assertEqual(response.status_code, 302)
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.is_public)
