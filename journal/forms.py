from django import forms
from django.forms.widgets import FileInput
from .models import JournalEntry, Comment, DailyRecord
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from django import forms
from .models import JournalEntry
from django.forms.widgets import FileInput

class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['answer_text', 'emotions', 'song_title', 'song_url', 'image']
        
        widgets = {
            'answer_text': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': "What's the story behind this track?",
                'class': "w-full px-4 py-2 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none"
            }),
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

class DailyRecordForm(forms.ModelForm):
    class Meta:
        model = DailyRecord
        fields = ['song_id', 'song_title', 'artist', 'preview_url', 'location', 'photo', 'emotion']
        widgets = {
            'song_id': forms.HiddenInput(),
            'song_title': forms.HiddenInput(),
            'artist': forms.HiddenInput(),
            'preview_url': forms.HiddenInput(),
            'emotion': forms.RadioSelect
        }



