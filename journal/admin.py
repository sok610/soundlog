from django.contrib import admin
from .models import Emotion, DailyRecord

# Register your models here.
@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "spotify_query", "color")
    search_fields = ("name", "slug")


@admin.register(DailyRecord)
class DailyRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "song_title", "artist", "emotion", "location", "created_at")
    search_fields = ("song_title", "artist", "location")
    list_filter = ("emotion", "created_at")
