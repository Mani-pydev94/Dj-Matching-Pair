from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('questionnaire', '0003_question_keys_option_active'),
    ]

    operations = [
        migrations.AddField(
            model_name='questionresponse',
            name='other_text',
            field=models.CharField(blank=True, default='', max_length=500),
        ),
    ]
