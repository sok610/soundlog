from .models import Notification

def unread_notification_count(request):
    if request.user.is_authenticated:
        count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    else:
        count = 0
    return {'unread_notification_count': count}
