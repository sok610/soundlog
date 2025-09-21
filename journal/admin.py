from django.contrib import admin
from .models import Emotion

# Register your models here.
@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "spotify_query", "color")
    search_fields = ("name", "slug")
