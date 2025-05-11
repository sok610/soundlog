from django import forms
from .models import JournalEntry, Comment
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['title', 'content', 'hashtags', 'emotions', 'song_title', 'song_url', 'lyric_snippet']
        widgets = {
            'song_title': forms.HiddenInput(),
            'song_url': forms.HiddenInput(),
        }

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'song_title', 'song_url']