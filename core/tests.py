from django.test import TestCase
from django.urls import reverse


class PrivacyPolicyPageTests(TestCase):
    def test_privacy_policy_is_public_and_renders_policy_content(self):
        response = self.client.get(reverse('privacy_policy'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Privacy Policy')
        self.assertContains(response, 'Optional AI features')
        self.assertContains(response, 'questionnaire answers are sent to Groq only after you give separate consent')
