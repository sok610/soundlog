from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Emotion(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True) # joy, sadness, etc.
    color = models.CharField(max_length=50, default="#f3f4f6") # background color
    spotify_query = models.CharField(max_length=100, blank=True, null=True)
    
    def __str__(self):
        return self.name
    
class Prompt(models.Model):
    TYPE_CHOICES = [
        ('DAILY', 'Daily Song Diary'),   
        ('PREFERENCE', 'Preference Profiling'),
    ]
    content = models.TextField()
    prompt_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='DAILY')
    created_at = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"[{self.prompt_type}] {self.content[:20]}..."

class JournalEntry(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    prompt = models.ForeignKey(Prompt, on_delete=models.SET_NULL, null=True, blank=True)
    
    answer_text = models.TextField() 
    
    image = models.ImageField(upload_to='entry_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name="liked_entries", blank=True)
    emotions = models.ManyToManyField(Emotion, blank=True)
    song_title = models.CharField(max_length=200, blank=True)
    song_url = models.URLField(blank=True)
    

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    following = models.ManyToManyField("self", symmetrical=False, related_name="followers", blank=True)

    def __str__(self):
        return self.user.username
    
class Comment(models.Model):
    entry = models.ForeignKey("JournalEntry", on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    song_title = models.CharField(max_length=100, blank=True)
    song_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.author.username} - {self.content[:20]}"
    
class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ("like", "Like"),
        ("comment", "Comment"),
        ("follow", "Follow"),
    ]
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_notifications')
    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    message = models.CharField(max_length=255)
    type = models.CharField(max_length=10, choices=NOTIFICATION_TYPES)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.recipient.username} - {self.message}"
    



User.profile = property(lambda u: Profile.objects.get_or_create(user=u)[0])


# journal/models.py
from django.db import models
from django.contrib.auth.models import User

EMOTION_CHOICES = [
    ('joy', 'Joy'),
    ('sadness', 'Sadness'),
    ('anger', 'Anger'),
    ('surprise', 'Surprise'),
    ('anticipation', 'Anticipation'),
]

class DailyRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    song_id = models.CharField(max_length=255, blank=True, null=True)
    song_title = models.CharField(max_length=255, blank=True, null=True)
    artist = models.CharField(max_length=255, blank=True, null=True)
    preview_url = models.URLField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    photo = models.ImageField(upload_to="daily_photos/", blank=True, null=True)
    emotion = models.ForeignKey("Emotion", on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date = models.DateField(null=True,blank=True)

    class Meta:
        unique_together = ('user', 'date')

    def __str__(self):
        return f"{self.user} - {self.date} - {self.song_title}"
    

class ProfileAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='profile_answers')
    prompt = models.ForeignKey(Prompt, on_delete=models.CASCADE)
    answer_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'prompt')

    def __str__(self):
        return f"{self.user.username}'s answer to {self.prompt.id}"

