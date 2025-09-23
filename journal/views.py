from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from django.views.decorators.cache import never_cache
from .forms import JournalEntryForm, CommentForm, DailyRecordForm
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from .models import JournalEntry, Profile, Comment, Emotion, Notification, DailyRecord
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .utils.spotify import SpotifyTokenManager
from .tasks import analyze_entry
from django.utils.timezone import now
from datetime import date
import requests
import random
import calendar

spotify_token_manager = SpotifyTokenManager(
    settings.SPOTIFY_CLIENT_ID,
    settings.SPOTIFY_CLIENT_SECRET
)

EMOTION_FEATURES = {
    "joy": {"min_valence": 0.6, "max_valence": 1.0, "min_energy": 0.5},
    "sadness": {"max_valence": 0.4, "min_acousticness": 0.6},
    "anger": {"min_energy": 0.7, "min_tempo": 100},
    "anticipation": {"min_valence": 0.5, "min_energy": 0.5},
    "surprise": {"min_valence": 0.4, "max_valence": 0.9, "min_danceability": 0.5},
}


EMOTION_GENRES = {
    "joy": ["pop", "dance", "indie-pop"],
    "sadness": ["acoustic", "piano", "chill"],
    "anger": ["rock", "metal", "punk"],
    "anticipation": ["hiphop", "pop", "edm"],
    "surprise": ["electronic", "edm", "indie-pop"],
}



# Create your views here.
def home(request):
    if request.user.is_authenticated:
        following_profiles = request.user.profile.following.all()

        following_users = [profile.user for profile in following_profiles]

        # user filter to bring the current user's entries
        entries = JournalEntry.objects.filter(
            author__in=[request.user] + following_users
        ).order_by("-created_at")

        for entry in entries:
            entry.hashtag_list = [tag.strip() for tag in entry.hashtags.split(',') if tag.strip()]

        return render(request, "journal/feed.html", {"entries": entries})
    else:
        return render(request, "journal/landing.html")

    
@login_required
def mood_calendar(request):
    today = now().date()
    year, month = today.year, today.month

    records = DailyRecord.objects.filter(
        user=request.user,
        created_at__year=year,
        created_at__month=month
    ).select_related("emotion") 

    # 날짜별 감정 색상 매핑
    record_map = {
        r.created_at.day: r.emotion.color if r.emotion else "#f3f4f6"
        for r in records
    }

    cal = calendar.Calendar(firstweekday=6)  # Sunday 시작
    month_days = cal.itermonthdays(year, month)
    calendar_days = [day if day != 0 else "" for day in month_days]

    return render(request, "journal/mood_calendar.html", {
        "calendar_days": calendar_days,
        "record_map": record_map,
        "month": month,
        "year": year,
    })



@login_required
def write_entry(request):
    if request.method == "POST":
        form = JournalEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.author = request.user
            entry.save()

            emotion_ids = request.POST.getlist("emotions")
            entry.emotions.set(emotion_ids)

            analyze_entry.delay(entry.id)

            return redirect("home")
    else:
        form = JournalEntryForm()
    
    emotions = Emotion.objects.all()
    return render(request, "journal/write.html", {"form": form, "emotions": emotions})

def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = CustomUserCreationForm()
    return render(request, "journal/signup.html", {"form": form})

def toggle_follow(request, username):
    if not request.user.is_authenticated:
        return redirect("login")
    
    target_user = get_object_or_404(User, username=username)
    target_profile = target_user.profile
    my_profile = request.user.profile

    if target_profile in my_profile.following.all():
        my_profile.following.remove(target_profile)
    else:
        my_profile.following.add(target_profile)

    my_profile.save()

    next_url = request.GET.get("next") or request.META.get("HTTP_REFERER") or reverse("home")
    return HttpResponseRedirect(next_url)


def user_profile(request, username):
    target_user = get_object_or_404(User, username=username)
    profile = target_user.profile
    entries = JournalEntry.objects.filter(author=target_user).order_by("-created_at")

    # check the following status
    is_own_profile = request.user == target_user
    is_following = False
    if request.user.is_authenticated and not is_own_profile:
        is_following = target_user.profile in request.user.profile.following.all()

    context = {
        "target_user": target_user,
        "profile": profile,
        "entries": entries,
        "is_own_profile": is_own_profile,
        "is_following": is_following,
        "follower_count": target_user.profile.followers.count()
    }
    return render(request, "journal/profile.html", context)

def following_list(request, username):
    user = get_object_or_404(User, username=username)
    following = [profile.user for profile in user.profile.following.all()]
    context = {
        "target_user": user,
        "following": following,
    }
    return render(request, "journal/following_list.html", context)

def followers_list(request, username):
    user = get_object_or_404(User, username=username)
    followers = [profile.user for profile in user.profile.followers.all()]

    context = {
        "target_user": user,
        "followers": followers,
    }
    return render(request, "journal/followers_list.html", context)

def toggle_like(request, entry_id):
    if not request.user.is_authenticated:
        return redirect("login")
    
    entry = get_object_or_404(JournalEntry, id=entry_id)

    # if you click a like, if you have already liked it, unlike
    # like otherwise
    if request.user in entry.likes.all():
        entry.likes.remove(request.user)
    else:
        entry.likes.add(request.user)
    
    return redirect(request.GET.get("next", "home"))

def toggle_like_ajax(request, entry_id):
    if not request.user.is_authenticated:
        return JsonResponse({"error": 'not_authenticated'}, status=403)
    
    entry = get_object_or_404(JournalEntry, id=entry_id)
    
    liked = False
    if request.user in entry.likes.all():
        entry.likes.remove(request.user)
    else:
        entry.likes.add(request.user)
        liked = True

        # Create notification
        if entry.author != request.user:
            Notification.objects.create(
                recipient=entry.author,
                sender=request.user,
                entry = entry,
                type="like",
                message=f"{request.user} liked your journal."
            )
    
    return JsonResponse({
        "liked": liked,
        "likes_count": entry.likes.count()
    })

def toggle_follow_ajax(request, username):
    if not request.user.is_authenticated:
        return JsonResponse({"error:", 'not_authenticated'}, status=403)
    
    target_user = get_object_or_404(User, username=username)
    target_profile = target_user.profile
    my_profile = request.user.profile

    is_following = False
    if target_profile in my_profile.following.all():
        my_profile.following.remove(target_profile)
    else:
        my_profile.following.add(target_profile)
        is_following = True
    
    return JsonResponse({"is_following": is_following})

def entry_detail(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id)
    comments = entry.comments.order_by("created_at")

    edit_comment_id = request.GET.get("edit_comment")
    delete_comment_id = request.GET.get("delete_comment")
    edit_comment_instance = None

    if edit_comment_id:
        edit_comment_instance = get_object_or_404(Comment, id=edit_comment_id, author=request.user, entry=entry)

    if delete_comment_id and request.method == "POST":
        comment_to_delete = get_object_or_404(Comment, id=delete_comment_id, author=request.user, entry=entry)
        comment_to_delete.delete()
        return redirect("entry_detail", entry_id=entry.id)

    if request.method == "POST" and not delete_comment_id:
        form = CommentForm(request.POST, instance=edit_comment_instance)  # 🔑 핵심 수정
        if form.is_valid():
            comment = form.save(commit=False)
            comment.entry = entry
            comment.author = request.user
            comment.save()

            # 수정이 아닌 새 댓글이라면 알림 생성
            if not edit_comment_instance and request.user != entry.author:
                Notification.objects.create(
                    recipient=entry.author,
                    sender=request.user,
                    comment=comment,
                    entry=entry,
                    type="comment",
                    message=f"{request.user} commented on your journal."
                )

            return redirect("entry_detail", entry_id=entry.id)

    else:
        form = CommentForm(instance=edit_comment_instance) if edit_comment_instance else CommentForm()

    return render(request, "journal/entry_detail.html", {
        "entry": entry,
        "comments": comments,
        "comments_count": comments.count(),
        "form": form,
        "edit_comment_id": int(edit_comment_id) if edit_comment_id else None,
        "delete_comment_id": int(delete_comment_id) if delete_comment_id else None,
    })



@login_required
def edit_entry(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id, author=request.user)
    
    if request.method == "POST":
        form = JournalEntryForm(request.POST, request.FILES, instance=entry)
        if form.is_valid():
            updated_entry = form.save(commit=False)
            updated_entry.author = request.user
            updated_entry.save()

            # update emotions
            selected_emotion_ids = request.POST.getlist('emotions')
            selected_emotions = Emotion.objects.filter(id__in=selected_emotion_ids)
            entry.emotions.set(selected_emotions)

            return redirect('user_profile', username=request.user.username)
    else:
        form = JournalEntryForm(instance=entry)
    
    selected_emotion_ids = [emotion.id for emotion in entry.emotions.all()]
    all_emotions = Emotion.objects.all()

    return render(request, 'journal/edit_entry.html', {
        'form': form,
        'emotions': all_emotions,
        'selected_emotion_ids': selected_emotion_ids,
    })

@login_required
def delete_entry(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id, author=request.user)
    if request.method == "POST":
        entry.delete()
        return redirect('user_profile', username=request.user.username)
    return render(request, 'journal/confirm_delete.html', {'entry': entry})

def search_music(request):
    query = request.GET.get("q")
    if not query:
        return JsonResponse({"tracks": []})
    
    token = spotify_token_manager.get_token()
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": query, "type": "track", "limit": 5}
    response = requests.get("https://api.spotify.com/v1/search", headers=headers, params=params)

    if response.status_code != 200:
        return JsonResponse({"tracks": []})
    
    items = response.json().get("tracks", {}).get("items", [])
    results = []
    for item in items:
        results.append({
            "id": item["id"],
            "name": item["name"],
            "artist": ", ".join(artist["name"] for artist in item["artists"]),
            "preview_url": item.get("preview_url"),
            "url": item["external_urls"]["spotify"],
        })
    
    return JsonResponse({"tracks": results})


def search_users(request):
    query = request.GET.get('q', '')
    results = []

    if query:
        results = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query)
        ).exclude(id=request.user.id)
    
    return render(request, 'journal/search_users.html', {
        'query': query,
        'results': results
    })

@never_cache
@login_required
def notification_list(request):
    notifications = request.user.notifications.order_by("-created_at")
    return render(request, 'journal/notification/list.html', {
        'notifications': notifications,
    })

def mark_notification_as_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, recipient=request.user)
    notification.is_read = True
    notification.save()

    if notification.comment:
        return redirect("entry_detail", entry_id=notification.entry.id)
    elif notification.entry:
        return redirect("entry_detail", entry_id=notification.entry.id)
    else:
        redirect("home")

    return redirect('entry_detail', entry_id=notification.entry.id if notification.entry else "home")

@login_required
def edit_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            return redirect('entry_detail', entry_id=comment.entry.id)
    else:
        form = CommentForm(instance=comment)
    return render(request, 'journal/edit_comment.html', {'form': form}, {'comment': comment})

@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id, author=request.user)
    if request.method == 'POST':
        comment.delete()
        return redirect('entry_detail', entry_id=comment.entry.id)
    return render(request, 'journal/edit_comment.html',{'comment': comment})


@login_required
def get_recommendations(request, entry_id):
    entry = get_object_or_404(JournalEntry, id=entry_id)

    keywords = entry.detected_keywords or []
    query = " ".join(keywords) if keywords else entry.detected_emotion or "chill"

    token = spotify_token_manager.get_token()
    headers = {"Authorization": f"Bearer {token}"}

    playlist_search = requests.get(
        "https://api.spotify.com/v1/search",
        headers=headers,
        params={"q": f"{query} playlist", "type": "playlist", "limit": 5, "market": "US"},
    )

    tracks = []
    if playlist_search.status_code == 200:
        playlists = playlist_search.json().get("playlists", {}).get("items", [])
        if playlists:
            top_playlist_id = playlists[0]["id"]

            track_response = requests.get(
                f"https://api.spotify.com/v1/playlists/{top_playlist_id}/tracks",
                headers=headers,
                params={"market": "US"},
            )

            if track_response.status_code == 200:
                all_tracks = [
                    {
                        "name": item["track"]["name"],
                        "artist": ", ".join(
                            a["name"] for a in (item["track"].get("artists") or []) if a.get("name")
                        ),
                        "url": item["track"]["external_urls"]["spotify"],
                        "image": (
                            item["track"]["album"]["images"][1]["url"]
                            if item["track"].get("album") and item["track"]["album"]["images"]
                            else None
                        ),
                        "popularity": item["track"].get("popularity", 0),
                    }
                    for item in track_response.json().get("items", [])
                    if item.get("track") and item["track"].get("name")
                ]


                all_tracks.sort(key=lambda x: x["popularity"], reverse=True)
                top_tracks = all_tracks[:20]
                tracks = random.sample(top_tracks, k=min(5, len(top_tracks)))

    return render(request, "journal/_recommendations.html", {"tracks": tracks, "query": query})


@login_required
def add_daily_record(request):
    today = now().date()
    existing_record = DailyRecord.objects.filter(
        user=request.user,
        created_at__date=today
    ).first()

    if existing_record:
        return redirect('view_daily_record', record_id=existing_record.id)

    if request.method == 'POST':
        form = DailyRecordForm(request.POST, request.FILES)
        if form.is_valid():
            daily_record = form.save(commit=False)
            daily_record.user = request.user
            daily_record.save()
            return redirect('home')
        else:
            print(form.errors)  # 🔥 터미널에 에러 출력
    else:
        form = DailyRecordForm()

    emotions = Emotion.objects.all()
    return render(request, 'journal/add_daily_record.html', {
        'form': form,
        'emotions': emotions,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY
    })


@login_required
def view_daily_record(request, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, user=request.user)
    return render(request, 'journal/view_daily_record.html', {'record': record})



