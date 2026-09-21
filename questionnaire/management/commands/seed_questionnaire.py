from django.core.management.base import BaseCommand

from questionnaire.services import seed_questionnaire_data


class Command(BaseCommand):
    help = 'Create or update the initial compatibility questionnaire.'

    def handle(self, *args, **options):
        count = seed_questionnaire_data()
        self.stdout.write(self.style.SUCCESS(f'Seeded {count} questionnaire questions across 6 categories.'))
