from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from communities.models import Community
from events.models import Event
from profiles.models import Profile
from questionnaire.models import Question, QuestionResponse


DEMO_STUDENTS = [
    ('Aarav', 'Sharma', 'aarav.demo@campusconnect.local', 'Computer Science', 'AI, Coding, Hackathons'),
    ('Priya', 'Nair', 'priya.demo@campusconnect.local', 'Data Science', 'AI, Research, Design'),
    ('Rohan', 'Mehta', 'rohan.demo@campusconnect.local', 'Business Analytics', 'Startups, Coding, Sports'),
    ('Ishita', 'Patel', 'ishita.demo@campusconnect.local', 'Information Technology', 'Cloud, Open Source, Photography'),
    ('Kabir', 'Khan', 'kabir.demo@campusconnect.local', 'Software Engineering', 'Coding, Web platforms, Music'),
]

COMMUNITIES = [
    ('AI & Machine Learning', 'Learn, experiment and share practical AI projects.', 'Technology'),
    ('Campus Founders', 'A friendly space for students building their first startup.', 'Entrepreneurship'),
    ('Design Thinkers', 'Exchange ideas about UX, product design and creative problem solving.', 'Design'),
    ('Open Source Circle', 'Find contributors and collaborators for meaningful open source work.', 'Technology'),
    ('Weekend Sports Club', 'Meet students who enjoy staying active and trying new sports.', 'Lifestyle'),
]

EVENTS = [
    ('Campus Hack Night', 'Build a useful project with a small team in one evening.', 'Innovation Lab'),
    ('AI Career Q&A', 'Ask industry mentors about careers in artificial intelligence.', 'Main Auditorium'),
    ('Design Sprint Workshop', 'Practice turning a student problem into a tested product idea.', 'Design Studio'),
    ('Open Source Contribution Day', 'Make your first contribution with support from experienced students.', 'Computer Lab 2'),
    ('Inter-college Sports Meetup', 'An informal afternoon of games and new connections.', 'University Ground'),
]


class Command(BaseCommand):
    help = 'Create five repeatable demo communities, events, and matching profiles.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            help='Email of the local user who should be added to demo communities and events.',
        )

    def handle(self, *args, **options):
        owner = self._get_owner(options.get('email'))
        demo_users = self._seed_students(owner)
        all_members = [user for user in [owner, *demo_users] if user]

        for name, description, category in COMMUNITIES:
            community, _ = Community.objects.update_or_create(
                name=name,
                defaults={'description': description, 'category': category},
            )
            community.members.set(all_members)

        start = timezone.now().replace(minute=0, second=0, microsecond=0)
        for index, (title, description, location) in enumerate(EVENTS, start=1):
            event, _ = Event.objects.update_or_create(
                title=title,
                defaults={
                    'description': description,
                    'start': start + timedelta(days=index * 2),
                    'location': location,
                },
            )
            event.attendees.set(all_members)

        self.stdout.write(self.style.SUCCESS(
            f'Created demo data: {len(COMMUNITIES)} communities, '
            f'{len(EVENTS)} events, and {len(demo_users)} matching profiles.'
        ))
        if owner and not getattr(owner, 'profile', None):
            self.stdout.write('Complete your profile and questionnaire to see demo matches on Home.')

    def _get_owner(self, email):
        if email:
            return User.objects.filter(email=email).first()
        return User.objects.order_by('created_at').first()

    def _seed_students(self, owner):
        questions = list(Question.objects.filter(is_active=True).prefetch_related('options'))
        source_responses = {}
        if owner:
            source_responses = {
                response.question_id: response
                for response in QuestionResponse.objects.filter(user=owner).prefetch_related('selected_options')
            }

        students = []
        for first_name, last_name, email, major, interests in DEMO_STUDENTS:
            student, _ = User.objects.get_or_create(
                email=email,
                defaults={'first_name': first_name, 'last_name': last_name},
            )
            changed = student.first_name != first_name or student.last_name != last_name
            if changed:
                student.first_name = first_name
                student.last_name = last_name
                student.save(update_fields=('first_name', 'last_name'))
            student.set_unusable_password()
            student.is_active = True
            student.save(update_fields=('password', 'is_active'))
            profile, _ = Profile.objects.get_or_create(user=student)
            profile.university = 'Campus Connect University'
            profile.major = major
            profile.year = '3rd Year'
            profile.city = 'Bengaluru'
            profile.languages = 'English, Hindi'
            profile.interests = interests
            profile.bio = f'{first_name} is looking for thoughtful student collaborators.'
            profile.is_public = True
            profile.questionnaire_completed = bool(questions)
            profile.save()
            self._copy_responses(student, questions, source_responses)
            students.append(student)
        return students

    @staticmethod
    def _copy_responses(student, questions, source_responses):
        for question in questions:
            source = source_responses.get(question.id)
            response, _ = QuestionResponse.objects.update_or_create(
                user=student,
                question=question,
                defaults={'value': source.value if source else (question.options.first().option_value if question.options.exists() else '1')},
            )
            if source:
                response.selected_options.set(source.selected_options.all())
            elif question.options.exists():
                response.selected_options.set([question.options.first()])
