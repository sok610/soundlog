from django.contrib import admin
from .models import Emotion

# Register your models here.
@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    list_display = ['name', 'color']
