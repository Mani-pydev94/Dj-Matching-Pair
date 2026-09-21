from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from .models import Question, QuestionOption, QuestionResponse
from .services import seed_questionnaire_data


class QuestionnaireAPITests(TestCase):
    def setUp(self):
        seed_questionnaire_data()
        self.user = User.objects.create_user(email='student@example.com', password='Strong-password-123')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.question = Question.objects.filter(is_active=True).first()
        self.option = self.question.options.first()

    def test_questions_and_categories_are_available(self):
        response = self.client.get('/api/questionnaire/questions/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 12)
        self.assertTrue(all(item['options'] for item in response.data))
        response = self.client.get('/api/questionnaire/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 6)

    def test_seed_is_idempotent(self):
        seed_questionnaire_data()
        self.assertEqual(Question.objects.count(), 12)
        self.assertEqual(QuestionOption.objects.count(), 61)

    def test_response_is_upserted_and_progress_updates(self):
        payload = {
            'question': str(self.question.id),
            'selected_option_ids': [str(self.option.id)],
        }
        response = self.client.post('/api/questionnaire/responses/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(QuestionResponse.objects.filter(user=self.user, question=self.question).count(), 1)
        response = self.client.post('/api/questionnaire/responses/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(QuestionResponse.objects.filter(user=self.user, question=self.question).count(), 1)
        progress = self.client.get('/api/questionnaire/progress/')
        self.assertEqual(progress.status_code, 200)
        self.assertEqual(progress.data['answered_questions'], 1)

    def test_option_from_another_question_is_rejected(self):
        other_question = Question.objects.exclude(id=self.question.id).first()
        other_option = other_question.options.first()
        response = self.client.post('/api/questionnaire/responses/', {
            'question': str(self.question.id),
            'selected_option_ids': [str(other_option.id)],
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_access_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/questionnaire/progress/').status_code, 403)
