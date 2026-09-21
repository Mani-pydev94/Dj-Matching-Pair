from django.db import migrations, models


def populate_question_keys(apps, schema_editor):
    Question = apps.get_model('questionnaire', 'Question')
    for index, question in enumerate(
        Question.objects.order_by('category', 'order', 'id'),
        start=1,
    ):
        question.question_key = f'Q{index:03d}'
        question.save(update_fields=('question_key',))


class Migration(migrations.Migration):
    dependencies = [
        ('questionnaire', '0002_questionnairecategory_question_help_text_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='question_key',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='questionoption',
            name='is_active',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(populate_question_keys, migrations.RunPython.noop),
    ]
