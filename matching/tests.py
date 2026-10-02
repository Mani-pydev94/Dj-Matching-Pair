from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from profiles.models import Profile
from questionnaire.models import Question, QuestionResponse
from questionnaire.services import seed_questionnaire_data
from connections.models import Connection
from .compatibility import calculate_compatibility, calculate_compatibility_analysis
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

    def test_question_importance_does_not_change_equal_question_scores(self):
        question_a, question_b = list(
            Question.objects.filter(is_active=True).order_by('category', 'order')[:2]
        )
        self.assertEqual(question_a.category, question_b.category)
        mismatch_b = QuestionResponse.objects.get(user=self.b, question=question_b)
        different_option = question_b.options.exclude(
            id=mismatch_b.selected_options.first().id,
        ).first()
        mismatch_b.selected_options.set([different_option])
        mismatch_a = QuestionResponse.objects.get(user=self.a, question=question_b)

        mismatch_a.importance = QuestionResponse.Importance.MOST_IMPORTANT
        mismatch_b.importance = QuestionResponse.Importance.MOST_IMPORTANT
        mismatch_a.save(update_fields=('importance',))
        mismatch_b.save(update_fields=('importance',))
        high_importance_score = calculate_compatibility(self.a, self.b)

        mismatch_a.importance = QuestionResponse.Importance.NOT_VERY_IMPORTANT
        mismatch_b.importance = QuestionResponse.Importance.NOT_VERY_IMPORTANT
        mismatch_a.save(update_fields=('importance',))
        mismatch_b.save(update_fields=('importance',))
        low_importance_score = calculate_compatibility(self.a, self.b)

        self.assertEqual(low_importance_score, high_importance_score)

    def test_overall_score_averages_questions_not_categories(self):
        questions = list(
            Question.objects.filter(is_active=True).order_by('category_ref__display_order', 'order')
        )
        weighted_questions = questions[:4]
        QuestionResponse.objects.filter(
            user__in=(self.a, self.b),
        ).exclude(question__in=weighted_questions).delete()

        first_response = QuestionResponse.objects.get(user=self.b, question=weighted_questions[0])
        first_response.selected_options.set([weighted_questions[0].options.last()])

        score = calculate_compatibility(self.a, self.b)

        self.assertEqual(score['overall_score'], 75)
        self.assertEqual(len(score['categories']), 9)
        self.assertEqual(score['categories']['mindset-worldview'], 67)
        self.assertEqual(score['categories']['emotions-relationships'], 100)

    def test_compatibility_analysis_groups_question_scores_by_average_importance(self):
        questions = list(Question.objects.filter(is_active=True).order_by('category', 'order')[:2])
        most_question, least_question = questions
        for user in (self.a, self.b):
            QuestionResponse.objects.filter(user=user, question=most_question).update(
                importance=QuestionResponse.Importance.MOST_IMPORTANT,
            )
            QuestionResponse.objects.filter(user=user, question=least_question).update(
                importance=QuestionResponse.Importance.NOT_VERY_IMPORTANT,
            )

        analysis = calculate_compatibility_analysis(self.a, self.b)

        self.assertEqual(len(analysis['categories']), 9)
        self.assertEqual(analysis['most_important_similarity'], 100)
        self.assertEqual(analysis['most_important_questions'][0]['question'], most_question.text)
        self.assertEqual(analysis['least_important_similarity'], 100)
        self.assertEqual(analysis['least_important_questions'][0]['question'], least_question.text)
        self.assertNotIn('shared_interests', analysis)
        self.assertNotIn('profile_factors', analysis)

    def test_compatibility_api_returns_anonymous_analysis_not_profile_data(self):
        question = Question.objects.filter(is_active=True).first()
        QuestionResponse.objects.filter(
            user__in=(self.a, self.b),
            question=question,
        ).update(importance=QuestionResponse.Importance.MOST_IMPORTANT)
        client = APIClient()
        client.force_authenticate(self.a)

        response = client.get(f'/api/matches/{self.b.id}/compatibility/')

        self.assertEqual(response.status_code, 200)
        self.assertIn('overall_score', response.data)
        self.assertIn('most_important_questions', response.data)
        self.assertEqual(
            set(response.data['most_important_questions'][0]),
            {'question', 'category', 'similarity', 'importance_weight'},
        )
        self.assertNotIn('shared_interests', response.data)
        self.assertNotIn('profile_factors', response.data)
        self.assertNotIn('display_name', response.data)
        self.assertNotIn('profile_photo', response.data)

    def test_compatibility_api_does_not_score_private_unconnected_profiles(self):
        self.b.profile.is_public = False
        self.b.profile.save(update_fields=('is_public',))
        client = APIClient()
        client.force_authenticate(self.a)

        response = client.get(f'/api/matches/{self.b.id}/compatibility/')

        self.assertEqual(response.status_code, 404)

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
        self.b.first_name = 'Bobby'
        self.b.last_name = 'Student'
        self.b.save(update_fields=('first_name', 'last_name'))
        self.client = APIClient()
        self.client.force_authenticate(self.a)
        response = self.client.get('/api/matches/?min_score=0')
        result = next(item for item in response.data['results'] if item['user_id'] == self.b.id)
        self.assertIsNone(result['profile_photo'])
        self.assertEqual(result['connection_status'], 'NONE')
        self.assertEqual(result['display_name'], '??? ???')
        self.assertNotIn('Bobby', result['display_name'])

    def test_matches_unlock_connected_profiles(self):
        self.b.first_name = 'Bobby'
        self.b.last_name = 'Student'
        self.b.save(update_fields=('first_name', 'last_name'))
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
        self.assertEqual(result['display_name'], 'Bobby Student')

    def test_matches_unlock_connected_status_profiles(self):
        Connection.objects.create(requester=self.a, recipient=self.b, status='CONNECTED')

        self.client = APIClient()
        self.client.force_authenticate(self.a)
        response = self.client.get('/api/matches/?min_score=0')
        result = next(item for item in response.data['results'] if item['user_id'] == self.b.id)

        self.assertEqual(result['connection_status'], 'CONNECTED')
        self.assertFalse(result['is_private'])

    def test_home_matches_mask_names_until_connection(self):
        self.b.first_name = 'Bobby'
        self.b.last_name = 'Student'
        self.b.save(update_fields=('first_name', 'last_name'))

        self.client = APIClient()
        self.client.force_login(self.a)
        response = self.client.get('/home/')

        self.assertContains(response, '??? ???')
        self.assertNotContains(response, 'Bobby Student')
        self.assertContains(response, 'avatar-placeholder private-avatar')

        Connection.objects.create(requester=self.a, recipient=self.b, status='ACCEPTED')
        response = self.client.get('/home/')

        self.assertContains(response, 'Bobby Student')

    def test_home_renders_all_matches_for_horizontal_scrolling(self):
        candidates = [self.b]
        for index in range(5):
            candidate = User.objects.create_user(
                email=f'candidate{index}@example.com',
                password='Strong-password-123',
            )
            Profile.objects.create(
                user=candidate,
                is_public=True,
                questionnaire_completed=True,
                interests='AI, Cloud',
            )
            for question in Question.objects.filter(is_active=True):
                QuestionResponse.objects.create(
                    user=candidate, question=question,
                ).selected_options.add(question.options.first())
            candidates.append(candidate)

        self.client = APIClient()
        self.client.force_login(self.a)
        response = self.client.get('/home/')

        self.assertEqual(response.status_code, 200)
        for candidate in candidates:
            self.assertContains(response, f'/profiles/{candidate.id}/')

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
