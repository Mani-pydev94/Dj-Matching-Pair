from django.test import Client, TestCase
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

    def test_questionnaire_hub_page_renders(self):
        page_client = Client()
        page_client.force_login(self.user)
        response = page_client.get('/questionnaire/hub/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your question topics')
        self.assertContains(response, '/api/questionnaire/categories/')
        self.assertContains(response, 'Continue questionnaire')

    def test_questions_page_shows_importance_choices(self):
        page_client = Client()
        page_client.force_login(self.user)
        response = page_client.get('/questionnaire/questions/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Compatibility Profile')
        self.assertContains(response, 'How important is this question to you?')
        self.assertContains(response, 'Very Important')
        self.assertContains(response, 'Somewhat Important')
        self.assertContains(response, 'Not Important')
        self.assertContains(response, 'Next Question')
        self.assertContains(response, 'aria-label="Main navigation"')
        self.assertContains(response, '>Home</span>')
        self.assertContains(response, '>Matches</span>')
        self.assertContains(response, '>Chat</span>')
        self.assertContains(response, '>Profile</span>')

    def test_seed_is_idempotent(self):
        seed_questionnaire_data()
        self.assertEqual(Question.objects.count(), 12)
        self.assertEqual(QuestionOption.objects.count(), 61)

    def test_response_is_upserted_and_progress_updates(self):
        payload = {
            'question': str(self.question.id),
            'selected_option_ids': [str(self.option.id)],
            'importance': 'MOST_IMPORTANT',
        }
        response = self.client.post('/api/questionnaire/responses/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['importance'], 'MOST_IMPORTANT')
        self.assertEqual(QuestionResponse.objects.filter(user=self.user, question=self.question).count(), 1)
        response = self.client.post('/api/questionnaire/responses/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(QuestionResponse.objects.filter(user=self.user, question=self.question).count(), 1)
        saved = QuestionResponse.objects.get(user=self.user, question=self.question)
        self.assertEqual(saved.importance, 'MOST_IMPORTANT')
        progress = self.client.get('/api/questionnaire/progress/')
        self.assertEqual(progress.status_code, 200)
        self.assertEqual(progress.data['answered_questions'], 1)

    def test_single_choice_other_answer_is_saved_and_returned(self):
        response = self.client.post('/api/questionnaire/responses/', {
            'question': str(self.question.id),
            'selected_option_ids': [],
            'other_text': 'A custom single-choice answer',
            'importance': 'NEUTRAL',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['other_text'], 'A custom single-choice answer')
        saved = QuestionResponse.objects.get(user=self.user, question=self.question)
        self.assertEqual(saved.other_text, 'A custom single-choice answer')

        response = self.client.get('/api/questionnaire/responses/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['other_text'], 'A custom single-choice answer')
        self.assertEqual(response.data[0]['importance'], 'NEUTRAL')

    def test_multiple_choice_saves_regular_and_other_answers(self):
        self.question.question_type = 'MULTIPLE_CHOICE'
        self.question.save(update_fields=('question_type',))
        response = self.client.post('/api/questionnaire/responses/', {
            'question': str(self.question.id),
            'selected_option_ids': [str(self.option.id)],
            'other_text': 'A custom multiple-choice answer',
            'importance': 'NOT_VERY_IMPORTANT',
        }, format='json')

        self.assertEqual(response.status_code, 201)
        saved = QuestionResponse.objects.get(user=self.user, question=self.question)
        self.assertEqual(saved.other_text, 'A custom multiple-choice answer')
        self.assertEqual(list(saved.selected_options.all()), [self.option])
        self.assertEqual(saved.importance, 'NOT_VERY_IMPORTANT')

    def test_importance_is_required_and_must_be_a_supported_choice(self):
        payload = {
            'question': str(self.question.id),
            'selected_option_ids': [str(self.option.id)],
        }
        response = self.client.post('/api/questionnaire/responses/', payload, format='json')
        self.assertEqual(response.status_code, 400)
        payload['importance'] = 'VERY_IMPORTANT'
        response = self.client.post('/api/questionnaire/responses/', payload, format='json')
        self.assertEqual(response.status_code, 400)

    def test_other_answer_requires_a_description(self):
        for question_type in ('SINGLE_CHOICE', 'MULTIPLE_CHOICE'):
            self.question.question_type = question_type
            self.question.save(update_fields=('question_type',))
            response = self.client.post('/api/questionnaire/responses/', {
                'question': str(self.question.id),
                'selected_option_ids': [],
                'other_text': '   ',
                'importance': 'NEUTRAL',
            }, format='json')
            self.assertEqual(response.status_code, 400)

    def test_option_from_another_question_is_rejected(self):
        other_question = Question.objects.exclude(id=self.question.id).first()
        other_option = other_question.options.first()
        response = self.client.post('/api/questionnaire/responses/', {
            'question': str(self.question.id),
            'selected_option_ids': [str(other_option.id)],
            'importance': 'NEUTRAL',
        }, format='json')
        self.assertEqual(response.status_code, 400)

    def test_unauthenticated_access_is_rejected(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get('/api/questionnaire/progress/').status_code, 403)
