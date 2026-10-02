from io import BytesIO
from pathlib import Path
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from accounts.models import User
from admin_dashboard.views import _parse_questionnaire_workbook
from questionnaire.models import Question, QuestionOption, QuestionnaireCategory


class QuestionnaireAdminTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='Strong-password-123',
            is_staff=True,
        )
        self.category = QuestionnaireCategory.objects.create(
            name='Values',
            slug='values',
        )
        self.client.force_login(self.user)

    def test_question_edit_manages_options(self):
        response = self.client.post(
            reverse('admin_dashboard:question_new'),
            {
                'question_key': 'Q001',
                'category_ref': self.category.id,
                'text': 'What matters most?',
                'question_type': 'SINGLE_CHOICE',
                'help_text': '',
                'order': 1,
                'weight': '1.0',
                'is_required': 'on',
                'is_active': 'on',
                'options-TOTAL_FORMS': '2',
                'options-INITIAL_FORMS': '0',
                'options-MIN_NUM_FORMS': '0',
                'options-MAX_NUM_FORMS': '1000',
                'options-0-option_text': 'Communication',
                'options-0-option_value': 'communication',
                'options-0-compatibility_value': '5',
                'options-0-display_order': '1',
                'options-0-is_active': 'on',
                'options-1-option_text': 'Reliability',
                'options-1-option_value': 'reliability',
                'options-1-compatibility_value': '4',
                'options-1-display_order': '2',
                'options-1-is_active': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(QuestionOption.objects.count(), 2)

    def test_question_fields_are_generated_on_save_when_blank(self):
        response = self.client.post(
            reverse('admin_dashboard:question_new'),
            {
                'question_key': '',
                'category_ref': self.category.id,
                'text': 'What stands out most?',
                'question_type': 'SINGLE_CHOICE',
                'help_text': '',
                'order': '',
                'weight': '1.0',
                'is_required': 'on',
                'is_active': 'on',
                'options-TOTAL_FORMS': '2',
                'options-INITIAL_FORMS': '0',
                'options-MIN_NUM_FORMS': '0',
                'options-MAX_NUM_FORMS': '1000',
                'options-0-option_text': 'Two people facing each other',
                'options-0-option_value': '',
                'options-0-compatibility_value': '1',
                'options-0-display_order': '',
                'options-0-is_active': 'on',
                'options-1-option_text': 'A mask or face',
                'options-1-option_value': '',
                'options-1-compatibility_value': '1',
                'options-1-display_order': '',
                'options-1-is_active': 'on',
            },
        )

        self.assertEqual(response.status_code, 302)
        question = Question.objects.get(text='What stands out most?')
        self.assertEqual(question.question_key, 'Q001')
        self.assertEqual(question.order, 0)
        self.assertEqual(
            list(question.options.order_by('display_order').values_list(
                'option_value', 'display_order',
            )),
            [('two-people-facing-each-other', 1), ('a-mask-or-face', 2)],
        )

    def test_question_editor_renders_dynamic_add_option_control(self):
        response = self.client.get(reverse('admin_dashboard:question_new'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="add-option"')
        self.assertContains(response, '+ Add option')
        self.assertContains(response, 'id="empty-option-form"')
        self.assertContains(response, 'options-__prefix__-option_text')

    def test_question_edit_uploads_image_questions_with_four_options(self):
        image_path = Path(__file__).resolve().parent.parent / 'media' / 'students.png'
        option_data = {}
        for index, option in enumerate(('First detail', 'Second detail', 'Third detail', 'Fourth detail')):
            option_data.update({
                f'options-{index}-option_text': option,
                f'options-{index}-option_value': f'detail-{index}',
                f'options-{index}-compatibility_value': '1',
                f'options-{index}-display_order': str(index + 1),
                f'options-{index}-is_active': 'on',
            })
        payload = {
            'question_key': 'VISUAL-001',
            'category_ref': self.category.id,
            'text': 'What stands out in this image?',
            'question_type': 'SINGLE_CHOICE',
            'help_text': '',
            'image_alt_text': 'Two students carrying tablets.',
            'order': 1,
            'weight': '1.0',
            'is_required': 'on',
            'is_active': 'on',
            'options-TOTAL_FORMS': '4',
            'options-INITIAL_FORMS': '0',
            'options-MIN_NUM_FORMS': '0',
            'options-MAX_NUM_FORMS': '1000',
            **option_data,
        }
        with tempfile.TemporaryDirectory() as media_root, override_settings(MEDIA_ROOT=media_root):
            payload['image'] = SimpleUploadedFile(
                'students.png',
                image_path.read_bytes(),
                content_type='image/png',
            )
            response = self.client.post(reverse('admin_dashboard:question_new'), payload)

            self.assertEqual(response.status_code, 302)
            question = Question.objects.get(question_key='VISUAL-001')
            self.assertTrue(question.image.name.startswith('questionnaire/questions/'))
            self.assertEqual(question.options.filter(is_active=True).count(), 4)

    def test_export_contains_questionnaire_columns(self):
        visual_question = Question.objects.create(
            category='Values',
            question_key='VISUAL-EXPORT',
            text='What stands out?',
            image='students.png',
        )
        QuestionOption.objects.create(
            question=visual_question,
            option_text='The students',
            option_value='students',
        )
        response = self.client.get(reverse('admin_dashboard:export_questionnaire'))

        self.assertEqual(response.status_code, 200)
        workbook = load_workbook(BytesIO(response.content), read_only=True)
        self.assertEqual(workbook.active.cell(1, 1).value, 'question_key')
        self.assertEqual(workbook.active.max_row, 1)

    def test_import_preview_does_not_write_until_confirmed(self):
        workbook = Workbook()
        sheet = workbook.active
        sheet.append([
            'question_key', 'category', 'question_text', 'question_type', 'help_text',
            'question_order', 'question_weight', 'is_required', 'is_active',
            'option_order', 'option_text', 'option_value', 'option_score',
            'option_is_active',
        ])
        sheet.append([
            'Q010', 'Values', 'What matters most?', 'SINGLE_CHOICE', '',
            1, 1.0, True, True, 1, 'Communication', 'communication', 5.0, True,
        ])
        file_data = BytesIO()
        workbook.save(file_data)
        rows, errors = _parse_questionnaire_workbook(
            SimpleUploadedFile(
                'questions.xlsx',
                file_data.getvalue(),
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            ),
        )

        self.assertEqual(errors, [])
        self.assertEqual(rows[0]['question_key'], 'Q010')
        self.assertFalse(Question.objects.filter(question_key='Q010').exists())

    def test_workbook_import_cannot_update_image_questions(self):
        question = Question.objects.create(
            category='Values',
            question_key='VISUAL-IMPORT',
            text='Original visual question',
            image='students.png',
        )
        session = self.client.session
        session['questionnaire_import_rows'] = [{'question_key': question.question_key}]
        session.save()

        response = self.client.post(reverse('admin_dashboard:questionnaire_import_export'), {
            'action': 'import',
            'mode': 'update',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Workbook import cannot create or update image questions.')
        question.refresh_from_db()
        self.assertEqual(question.text, 'Original visual question')
