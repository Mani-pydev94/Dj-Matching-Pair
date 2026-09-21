from django.db import migrations, models


def make_profiles_public(apps, schema_editor):
    Profile = apps.get_model('profiles', 'Profile')
    Profile.objects.filter(is_public=False).update(is_public=True)


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0003_profile_questionnaire_completed'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='is_public',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(make_profiles_public, migrations.RunPython.noop),
    ]
