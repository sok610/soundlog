from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Emotion(models.Model):
    name = models.CharField(max_length=50)
    slug = models.SlugField(unique=True) # joy, sadness, etc.
    color = models.CharField(max_length=50, default="#f3f4f6") # background color

    def __str__(self):
        return self.name

class JournalEntry(models.Model):
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    content = models.TextField()
    hashtags = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    likes = models.ManyToManyField(User, related_name="liked_entries", blank=True)
    emotions = models.ManyToManyField(Emotion, blank=True, related_name='entries')

    # music-related fields
    song_title = models.CharField(max_length=200, blank=True)
    song_url = models.URLField(blank=True)
    lyric_snippet = models.TextField(blank=True)

    def __str__(self):
        return f"{self.title} by {self.author.username}"
    

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
