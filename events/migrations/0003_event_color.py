from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('events', '0002_eventregistration'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='color',
            field=models.CharField(default='#7C4DFF', max_length=7),
        ),
    ]
