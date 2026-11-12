from django.db import migrations

COMPLEMENTARY_CATEGORY_SLUGS = {
    'weird-funny-personality',
    'friendship-social-energy',
    'lifestyle-experiences',
    'curiosity-room',
}
SIMILARITY_QUESTION_KEYS = {'curiosity-room-002'}


def tag_existing_questions(apps, schema_editor):
    Question = apps.get_model('questionnaire', 'Question')
    Question.objects.filter(
        category_ref__slug__in=COMPLEMENTARY_CATEGORY_SLUGS,
    ).exclude(question_key__in=SIMILARITY_QUESTION_KEYS).update(
        score_type='COMPLEMENTARY',
    )


def reset_question_types(apps, schema_editor):
    Question = apps.get_model('questionnaire', 'Question')
    Question.objects.all().update(score_type='SIMILARITY')


class Migration(migrations.Migration):
    dependencies = [
        ('questionnaire', '0008_question_score_type_questionnaireinsight_vibe_card'),
    ]

    operations = [
        migrations.RunPython(tag_existing_questions, reset_question_types),
    ]
