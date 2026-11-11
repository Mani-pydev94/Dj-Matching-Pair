from django.test import TestCase
from django.urls import reverse

from accounts.models import User

from .models import Community


def make_user(email, **extra):
    return User.objects.create_user(email=email, password='testpass123', **extra)


class CommunitiesViewTests(TestCase):
    def setUp(self):
        self.user = make_user('communities@example.com')
        self.client.force_login(self.user)
        self.community = Community.objects.create(name='Techno Lovers', category='Music')

    def test_home_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('communities_home'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/auth/login/', response.url)

    def test_home_shows_member_counts_and_categories(self):
        self.community.members.add(self.user)
        response = self.client.get(reverse('communities_home'))
        self.assertContains(response, 'Techno Lovers')
        self.assertContains(response, 'Music')
        self.assertIn(self.community, response.context['joined_communities'])

    def test_search_filters_by_name_description_or_category(self):
        response = self.client.get(reverse('communities_home'), {'q': 'techno'})
        self.assertIn(self.community, response.context['communities'])
        other = Community.objects.create(name='House Headliners', category='Music')
        response = self.client.get(reverse('communities_home'), {'q': 'house headliners'})
        self.assertIn(other, response.context['communities'])
        self.assertNotIn(self.community, response.context['communities'])

    def test_category_filter_with_all_shows_everything(self):
        response = self.client.get(reverse('communities_home'), {'category': 'All'})
        self.assertIn(self.community, response.context['communities'])
        response = self.client.get(reverse('communities_home'), {'category': 'Music'})
        self.assertIn(self.community, response.context['communities'])
        response = self.client.get(reverse('communities_home'), {'category': 'Gaming'})
        self.assertNotIn(self.community, response.context['communities'])

    def test_detail_404s_for_unknown_community(self):
        response = self.client.get(reverse('community_detail', args=[999999]))
        self.assertEqual(response.status_code, 404)

    def test_membership_toggle_join_then_leave(self):
        response = self.client.post(
            reverse('toggle_membership', args=[self.community.id]),
            {'next': '/communities/'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.community.members.filter(id=self.user.id).exists())
        response = self.client.post(
            reverse('toggle_membership', args=[self.community.id]),
            {'next': '/communities/'},
        )
        self.assertFalse(self.community.members.filter(id=self.user.id).exists())

    def test_membership_toggle_requires_post(self):
        response = self.client.get(reverse('toggle_membership', args=[self.community.id]))
        self.assertEqual(response.status_code, 405)

    def test_can_create_flag_is_superuser_only(self):
        response = self.client.get(reverse('communities_home'))
        self.assertFalse(response.context['can_create'])
        admin = make_user('admin@example.com', is_superuser=True, is_staff=True)
        self.client.force_login(admin)
        response = self.client.get(reverse('communities_home'))
        self.assertTrue(response.context['can_create'])
