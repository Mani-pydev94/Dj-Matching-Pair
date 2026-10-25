from io import StringIO
import json
import os
from unittest.mock import Mock, patch

from django.core.management import call_command, CommandError
from django.test import Client, TestCase
from rest_framework.test import APIClient

from accounts.models import User
from profiles.models import Profile
from .models import Question, QuestionOption, QuestionResponse, QuestionnaireCategory
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
        self.assertEqual(len(response.data), 24)
        self.assertTrue(all(item['options'] for item in response.data))
        response = self.client.get('/api/questionnaire/categories/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 9)
        visual_category = next(item for item in response.data if item['slug'] == 'visual-images')
        self.assertEqual(visual_category['question_count'], 0)

    def test_questions_follow_category_display_order(self):
        later_category = QuestionnaireCategory.objects.create(
            name='A later category',
            slug='test-later-category',
            display_order=2,
        )
        earlier_category = QuestionnaireCategory.objects.create(
            name='Z earlier category',
            slug='test-earlier-category',
            display_order=1,
        )
        questions = [
            Question.objects.create(
                category='A later category',
                category_ref=later_category,
                text='Later category question 2',
                order=2,
            ),
            Question.objects.create(
                category='A later category',
                category_ref=later_category,
                text='Later category question 1',
                order=1,
            ),
            Question.objects.create(
                category='Z earlier category',
                category_ref=earlier_category,
                text='Earlier category question 2',
                order=2,
            ),
            Question.objects.create(
                category='Z earlier category',
                category_ref=earlier_category,
                text='Earlier category question 1',
                order=1,
            ),
        ]

        response = self.client.get('/api/questionnaire/questions/')

        self.assertEqual(response.status_code, 200)
        displayed_ids = [item['id'] for item in response.data]
        expected_ids = [
            str(question.id)
            for question in (
                questions[3],
                questions[2],
                questions[1],
                questions[0],
            )
        ]
        self.assertEqual(
            [question_id for question_id in displayed_ids if question_id in expected_ids],
            expected_ids,
        )

    def test_questions_can_be_filtered_by_category_slug(self):
        category = QuestionnaireCategory.objects.filter(
            questions__is_active=True,
        ).distinct().first()

        response = self.client.get(
            '/api/questionnaire/questions/',
            {'category': category.slug},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data)
        self.assertTrue(all(question['category'] == category.slug for question in response.data))

    def test_questionnaire_hub_page_renders(self):
        page_client = Client()
        page_client.force_login(self.user)
        Profile.objects.create(user=self.user, questionnaire_ai_consent=False)
        response = page_client.get('/questionnaire/hub/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your question topics')
        self.assertContains(response, '/api/questionnaire/categories/')
        self.assertContains(response, 'Continue questionnaire')
        self.assertContains(response, '?category=${encodeURIComponent(category.slug)}')

    def test_questions_page_shows_importance_choices(self):
        page_client = Client()
        page_client.force_login(self.user)
        Profile.objects.create(user=self.user, questionnaire_ai_consent=False)
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

    def test_seed_command_replaces_questions_answers_and_completion_state(self):
        QuestionResponse.objects.create(user=self.user, question=self.question)
        Profile.objects.create(
            user=self.user,
            questionnaire_completed=True,
        )
        output = StringIO()
        call_command('seed_questionnaire', replace=True, stdout=output)

        self.assertEqual(Question.objects.count(), 24)
        self.assertEqual(QuestionOption.objects.count(), 94)
        self.assertEqual(QuestionnaireCategory.objects.count(), 9)
        self.assertEqual(QuestionResponse.objects.count(), 0)
        self.assertFalse(Profile.objects.get(user=self.user).questionnaire_completed)
        self.assertFalse(Question.objects.filter(question_key='VISUAL-001').exists())
        self.assertIn('24 questions across 9 categories', output.getvalue())

    def test_seed_command_requires_explicit_replacement_confirmation(self):
        with self.assertRaises(CommandError):
            call_command('seed_questionnaire')
        self.assertEqual(Question.objects.count(), 24)

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


class QuestionnaireSummaryTests(TestCase):
    def setUp(self):
        seed_questionnaire_data()
        self.user = User.objects.create_user(
            email='summary@example.com',
            password='Strong-password-123',
        )
        Profile.objects.create(
            user=self.user,
            questionnaire_completed=True,
            questionnaire_ai_consent=None,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        questions = Question.objects.filter(is_active=True).order_by(
            'category_ref__display_order',
            'order',
        )
        for index, question in enumerate(questions):
            importance = (
                QuestionResponse.Importance.MOST_IMPORTANT
                if index < 3
                else QuestionResponse.Importance.NEUTRAL
            )
            response = QuestionResponse.objects.create(
                user=self.user,
                question=question,
                importance=importance,
            )
            response.selected_options.add(question.options.first())

    def test_summary_only_includes_answered_categories_and_reports_ai_consent(self):
        response = self.client.get('/api/questionnaire/summary/')

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data['ai_consent'])
        self.assertEqual(response.data['overall_score'], 56)
        self.assertEqual(len(response.data['categories']), 8)
        self.assertEqual(response.data['categories'][0]['score'], 100)
        self.assertEqual(response.data['categories'][0]['summary_source'], 'pending')
        self.assertEqual(response.data['categories'][0]['summary'], '')
        self.assertIn('not a personality', response.data['overall_label'].lower())
        self.assertEqual(
            response.data['strongest_category']['name'],
            'Mindset & Worldview',
        )

    def test_summary_api_reports_saved_ai_opt_in(self):
        self.user.profile.questionnaire_ai_consent = True
        self.user.profile.save(update_fields=('questionnaire_ai_consent',))

        response = self.client.get('/api/questionnaire/summary/')

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['ai_consent'])

    def test_summary_page_requires_completed_questionnaire(self):
        page_client = Client()
        page_client.force_login(self.user)

        response = page_client.get('/questionnaire/summary/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'A little about you')
        self.assertNotContains(response, 'What does this percentage mean?')
        self.assertContains(response, 'Explore my matches')
        self.assertContains(response, 'Personal reflections, based on your answers.')
        self.assertContains(response, 'id="score-chart"')
        self.assertContains(response, 'id="score-legend"')
        self.assertContains(response, 'generateReflections()')
        self.assertContains(response, 'data.ai_consent && data.ai_configured')
        self.assertNotContains(response, 'Generate my reflections')

    def test_intro_requires_and_saves_ai_consent_choice(self):
        page_client = Client()
        page_client.force_login(self.user)
        response = page_client.get('/questionnaire/intro/')
        self.assertContains(response, 'Allow AI reflections and continue')
        self.assertContains(response, 'Continue without AI')
        self.assertContains(response, 'Google Gemini')

        response = page_client.post('/questionnaire/intro/', {'ai_consent': 'yes'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/questionnaire/hub/')
        self.user.profile.refresh_from_db()
        self.assertIs(self.user.profile.questionnaire_ai_consent, True)

        response = page_client.post('/questionnaire/intro/', {'ai_consent': 'no'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/questionnaire/hub/')
        self.user.profile.refresh_from_db()
        self.assertIs(self.user.profile.questionnaire_ai_consent, False)

    def test_questionnaire_pages_require_a_saved_consent_choice(self):
        QuestionResponse.objects.filter(user=self.user).first().delete()
        self.user.profile.questionnaire_completed = False
        self.user.profile.save(update_fields=('questionnaire_completed',))
        page_client = Client()
        page_client.force_login(self.user)

        self.assertRedirects(
            page_client.get('/questionnaire/hub/'),
            '/questionnaire/intro/',
        )
        self.assertRedirects(
            page_client.get('/questionnaire/questions/'),
            '/questionnaire/intro/',
        )

    def test_summary_api_rejects_incomplete_questionnaire(self):
        QuestionResponse.objects.filter(user=self.user).first().delete()

        response = self.client.get('/api/questionnaire/summary/')

        self.assertEqual(response.status_code, 403)

    def test_stale_completion_flag_does_not_loop_between_summary_and_hub(self):
        QuestionResponse.objects.filter(user=self.user).first().delete()
        self.user.profile.questionnaire_ai_consent = False
        self.user.profile.save(update_fields=('questionnaire_ai_consent',))
        page_client = Client()
        page_client.force_login(self.user)

        response = page_client.get('/questionnaire/hub/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Your question topics')

    def test_hub_redirects_to_summary_when_all_answers_are_complete(self):
        self.user.profile.questionnaire_completed = False
        self.user.profile.save(update_fields=('questionnaire_completed',))
        page_client = Client()
        page_client.force_login(self.user)

        response = page_client.get('/questionnaire/hub/')

        self.assertRedirects(response, '/questionnaire/summary/')
        self.user.profile.refresh_from_db()
        self.assertTrue(self.user.profile.questionnaire_completed)
        self.assertTrue(self.user.profile.is_public)

    def test_ai_insights_require_explicit_consent(self):
        response = self.client.post(
            '/api/questionnaire/summary/insights/',
            {'consent': False},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_ai_insights_reject_consent_not_saved_on_profile(self):
        response = self.client.post(
            '/api/questionnaire/summary/insights/',
            {'consent': True},
            format='json',
        )

        self.assertEqual(response.status_code, 403)

    @patch.dict(os.environ, {}, clear=True)
    def test_ai_insights_report_missing_gemini_configuration(self):
        self.user.profile.questionnaire_ai_consent = True
        self.user.profile.save(update_fields=('questionnaire_ai_consent',))
        response = self.client.post(
            '/api/questionnaire/summary/insights/',
            {'consent': True},
            format='json',
        )

        self.assertEqual(response.status_code, 503)
        self.assertIn('not configured', response.data['detail'])

    @patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'})
    @patch('questionnaire.summary.requests.post')
    def test_ai_insights_are_validated_and_cached(self, post):
        self.user.profile.questionnaire_ai_consent = True
        self.user.profile.save(update_fields=('questionnaire_ai_consent',))
        post_response = Mock()
        post_response.raise_for_status.return_value = None
        summaries = [
            {
                'slug': category.slug,
                'summary': f'Your answers suggest a thoughtful approach to {category.name.lower()}.',
            }
            for category in QuestionnaireCategory.objects.filter(is_active=True)
            if category.questions.filter(is_active=True, responses__user=self.user).exists()
        ]
        post_response.json.return_value = {
            'candidates': [{
                'content': {
                    'parts': [{
                        'text': json.dumps({'summaries': summaries}),
                    }],
                },
            }],
        }
        post.return_value = post_response

        response = self.client.post(
            '/api/questionnaire/summary/insights/',
            {'consent': True},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data['ai_generated'])
        self.assertEqual(
            {category['summary_source'] for category in response.data['categories']},
            {'ai'},
        )
        post.assert_called_once()
        self.assertEqual(
            post.call_args.kwargs['headers']['x-goog-api-key'],
            'test-key',
        )
        prompt = post.call_args.kwargs['json']['contents'][0]['parts'][0]['text']
        prompt_data = json.loads(prompt.split('\n\n', 1)[1])
        self.assertIn('pattern across all supplied question-and-answer pairs', prompt)
        self.assertEqual(len(prompt_data['categories']), 8)
        self.assertTrue(all(
            set(answer) == {'question', 'answer'}
            for category in prompt_data['categories']
            for answer in category['answers']
        ))
        self.assertEqual(
            sum(len(category['answers']) for category in prompt_data['categories']),
            QuestionResponse.objects.filter(user=self.user).count(),
        )
        cached_response = self.client.post(
            '/api/questionnaire/summary/insights/',
            {'consent': True},
            format='json',
        )
        self.assertEqual(cached_response.status_code, 200)
        post.assert_called_once()
