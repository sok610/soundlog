from django.db import migrations

def populate_emotions(apps, schema_editor):
    Emotion = apps.get_model("journal", "Emotion")
    default_data = [
        ("joy", "Joy", "#fef3c7", "happy upbeat"),
        ("sadness", "Sadness", "#e0e7ff", "sad acoustic"),
        ("anger", "Anger", "#fecaca", "angry rock"),
        ("surprise", "Surprise", "#d1fae5", "party edm"),
        ("anticipation", "Anticipation", "#fce7f3", "motivational"),
        ("pride", "Pride", "#ede9fe", "motivational pop"),
        ("fear", "Fear", "#f3f4f6", "calm soothing"),
    ]

    for slug, name, color, query in default_data:
        emotion, created = Emotion.objects.get_or_create(slug=slug, defaults={"name": name})
        emotion.color = color
        emotion.spotify_query = query
        emotion.save()

class Migration(migrations.Migration):

    dependencies = [
        ('journal', '0017_emotion_spotify_query'),
    ]

    operations = [
        migrations.RunPython(populate_emotions),
    ]


