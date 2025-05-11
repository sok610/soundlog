from django.core.management.base import BaseCommand
from journal.models import Emotion

class Command(BaseCommand):
    help = 'Initialize default emotions'

    def handle(self, *args, **kwargs):
        emotions = [
            ("Joy", "joy", "#fae3a0"),
            ("Sadness", "sadness", "#bcd4f6"),
            ("Anger", "anger", "#f8ccc0"),
            ("Surprise", "surprise", "#fcdde4"),
            ("Anticipation", "anticipation", "#d1edea"),
        ]

        for name, slug, color in emotions:
            Emotion.objects.get_or_create(name=name, slug=slug, defaults={'color': color})
        
        self.stdout.write(self.style.SUCCESS("Default emotions created."))