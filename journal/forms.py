from django import forms
from django.forms.widgets import FileInput
from .models import JournalEntry, Comment
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['title', 'content', 'hashtags', 'emotions', 'song_title', 'song_url', 'lyric_snippet', 'image']
        widgets = {
            'song_title': forms.HiddenInput(),
            'song_url': forms.HiddenInput(),
            'image': FileInput(attrs={
                'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-300'
            })
        }

class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'email']

class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content', 'song_title', 'song_url']