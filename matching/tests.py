from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from profiles.models import Profile
from questionnaire.models import Question, QuestionResponse
from questionnaire.services import seed_questionnaire_data
from connections.models import Connection
from .compatibility import calculate_compatibility
from .services import is_discoverable, score_match


class CompatibilityTests(TestCase):
    def setUp(self):
        seed_questionnaire_data()
        self.a = User.objects.create_user(email='a@example.com', password='Strong-password-123')
        self.b = User.objects.create_user(email='b@example.com', password='Strong-password-123')
        Profile.objects.create(user=self.a, is_public=True, questionnaire_completed=True, interests='AI, Cloud')
        Profile.objects.create(user=self.b, is_public=True, questionnaire_completed=True, interests='AI, Cloud')
        for question in Question.objects.filter(is_active=True):
            option = question.options.first()
            QuestionResponse.objects.create(user=self.a, question=question).selected_options.add(option)
            QuestionResponse.objects.create(user=self.b, question=question).selected_options.add(option)

    def test_same_answers_are_deterministic_and_high(self):
        first = calculate_compatibility(self.a, self.b)
        second = calculate_compatibility(self.a, self.b)
        self.assertEqual(first, second)
        self.assertGreaterEqual(first['overall_score'], 75)

    def test_matches_endpoint_excludes_self(self):
        client = APIClient()
        client.force_authenticate(self.a)
        response = client.get('/api/matches/?min_score=0')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(all(item['user_id'] != self.a.id for item in response.data['results']))

    def test_identical_public_profiles_appear_in_both_directions(self):
        self.a.profile.university = 'ABC University'
        self.b.profile.university = 'ABC University'
        self.a.profile.save()
        self.b.profile.save()

        client = APIClient()
        client.force_authenticate(self.a)
        self.assertIn(self.b.id, {item['user_id'] for item in client.get('/api/matches/?min_score=0').data['results']})
        client.force_authenticate(self.b)
        self.assertIn(self.a.id, {item['user_id'] for item in client.get('/api/matches/?min_score=0').data['results']})

    def test_same_university_is_discoverable_below_strong_match_threshold(self):
        self.b.profile.university = 'ABC University'
        self.a.profile.university = 'ABC University'
        self.a.profile.save()
        self.b.profile.save()
        for response in QuestionResponse.objects.filter(user=self.b).order_by('question__order')[6:]:
            response.selected_options.clear()
            response.value = 'different'
            response.save(update_fields=('value',))
        breakdown = score_match(self.a, self.b)
        self.assertLess(breakdown['overall_score'], 75)
        self.assertTrue(is_discoverable(self.a, self.b, breakdown))

    def test_same_university_is_discoverable_without_questionnaire_match(self):
        self.a.profile.university = 'ABC University'
        self.b.profile.university = 'ABC University'
        self.a.profile.save()
        self.b.profile.save()
        for response in QuestionResponse.objects.filter(user=self.b):
            response.selected_options.clear()
            response.value = 'different-answer'
            response.save(update_fields=('value',))
        breakdown = score_match(self.a, self.b)
        self.assertEqual(breakdown['questionnaire_score'], 0)
        self.assertTrue(is_discoverable(self.a, self.b, breakdown))

    def test_matches_do_not_expose_photo_before_connection(self):
        self.client = APIClient()
        self.client.force_authenticate(self.a)
        response = self.client.get('/api/matches/?min_score=0')
        result = next(item for item in response.data['results'] if item['user_id'] == self.b.id)
        self.assertIsNone(result['profile_photo'])
        self.assertEqual(result['connection_status'], 'NONE')

    def test_matches_unlock_connected_profiles(self):
        Connection.objects.create(requester=self.a, recipient=self.b, status='ACCEPTED')
        self.b.profile.university = 'ABC University'
        self.b.profile.major = 'Computer Science'
        self.b.profile.save()
        self.client = APIClient()
        self.client.force_authenticate(self.a)

        response = self.client.get('/api/matches/?min_score=0')
        result = next(item for item in response.data['results'] if item['user_id'] == self.b.id)

        self.assertEqual(result['connection_status'], 'ACCEPTED')
        self.assertFalse(result['is_private'])
        self.assertEqual(result['university'], 'ABC University')
        self.assertEqual(result['field_of_study'], 'Computer Science')

    def test_same_university_match_is_bidirectional_for_incomplete_questionnaire(self):
        self.b.profile.questionnaire_completed = False
        self.b.profile.university = 'ABC University'
        self.a.profile.university = 'ABC University'
        self.a.profile.save()
        self.b.profile.save()

        client = APIClient()
        client.force_authenticate(self.a)
        response = client.get('/api/matches/?min_score=75')

        self.assertIn(self.b.id, {item['user_id'] for item in response.data['results']})
