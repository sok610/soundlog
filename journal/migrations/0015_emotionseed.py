from django.db import migrations

def create_emotions(apps, schema_editor):
    Emotion = apps.get_model('journal', 'Emotion')
    Emotion.objects.bulk_create([
        Emotion(name="Joy", color="#fae3a0", slug="joy"),
        Emotion(name="Sadness", color="#bcd4f6", slug="sadness"),
        Emotion(name="Anger", color="#f8ccc0", slug="anger"),
        Emotion(name="Surprise", color="#fcdde4", slug="surprise"),
        Emotion(name="Anticipation", color="#d1edea", slug="anticipation"),
    ])

class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0014_journalentry_image'),  # 기존 migration 이름으로 변경
    ]

    operations = [
        migrations.RunPython(create_emotions),
    ]
