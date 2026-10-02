from django.core.management.base import BaseCommand, CommandError

from questionnaire.services import seed_questionnaire_data


class Command(BaseCommand):
    help = 'Replace the questionnaire categories and questions with the current set.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--replace',
            action='store_true',
            help='Confirm deletion of existing questionnaire questions, options, and responses.',
        )

    def handle(self, *args, **options):
        if not options['replace']:
            raise CommandError(
                'This command deletes existing questions and their saved responses. '
                'Run it again with --replace to confirm.'
            )
        count = seed_questionnaire_data()
        self.stdout.write(self.style.SUCCESS(
            f'Replaced questionnaire data with {count} questions across 9 categories.'
        ))
