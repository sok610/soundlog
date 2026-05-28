from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone
from .models import Prompt, ProfileAnswer
from django.views.decorators.cache import never_cache
from .forms import JournalEntryForm, CommentForm, DailyRecordForm
from django.contrib.auth import login
from .forms import CustomUserCreationForm
from django.contrib.auth.decorators import login_required
from .models import JournalEntry, Profile, Comment, Emotion, Notification, DailyRecord
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from .constants import EMOTION_GENRES, EMOTION_FEATURES, DEFAULT_GENRES
from .utils.spotify import SpotifyTokenManager
from collections import defaultdict
from .tasks import analyze_entry
from django.utils.timezone import now
from django.utils import timezone
import pytz
from datetime import date
import requests
import random
import calendar
import time
import logging
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.cache import cache

try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except ImportError:
    pass

def convert_heic_if_needed(image_file):
    if not image_file or not image_file.name.lower().endswith('.heic'):
        return image_file
    try:
        from PIL import Image
        img = Image.open(image_file).convert('RGB')
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        new_name = image_file.name.rsplit('.', 1)[0] + '.jpg'
        return ContentFile(buffer.getvalue(), name=new_name)
    except Exception:
        return image_file


spotify_token_manager = SpotifyTokenManager(
    settings.SPOTIFY_CLIENT_ID,
    settings.SPOTIFY_CLIENT_SECRET
)

# Reuse HTTP connections and retry transient failures
_session = requests.Session()
try:
    from urllib3.util.retry import Retry
    from requests.adapters import HTTPAdapter
    _retries = Retry(
        total=3,
        backoff_factor=0.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    _adapter = HTTPAdapter(max_retries=_retries, pool_connections=10, pool_maxsize=10)
    _session.mount("https://", _adapter)
    _session.mount("http://", _adapter)
except Exception:
    pass

# Create your views here.
def home(request):
    if request.user.is_authenticated:
        following_profiles = request.user.profile.following.all()
        following_users = [profile.user for profile in following_profiles]
        entries = JournalEntry.objects.filter(
            author__in=[request.user] + following_users
        ).order_by("-created_at")

        user_tz = pytz.timezone('America/Los_Angeles')
        today_in_la = timezone.now().astimezone(user_tz).date()
        today_prompt = Prompt.objects.filter(
            prompt_type='DAILY', created_at=today_in_la
        ).last()
        if not today_prompt:
            today_prompt = Prompt.objects.filter(prompt_type='DAILY').order_by('-created_at').first()

        return render(request, "journal/feed.html", {"entries": entries, "today_prompt": today_prompt})
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

    # 날짜별 감정 색상 매핑 (리스트)
    record_map = defaultdict(list)
    for r in records:
        if r.date:
            record_map[r.date.day].append(r.emotion.color if r.emotion else "#f3f4f6")

    day_color_map = {day: colors[0] for day, colors in record_map.items()}

    cal = calendar.Calendar(firstweekday=6)
    month_days = cal.itermonthdays(year, month)
    calendar_days = [day if day != 0 else "" for day in month_days]

    return render(request, "journal/mood_calendar.html", {
        "calendar_days": calendar_days,
        "record_map": day_color_map,
        "month": month,
        "year": year,
    })



@login_required
def write_entry(request):
    user_tz = pytz.timezone('America/Los_Angeles')
    today_in_la = timezone.now().astimezone(user_tz).date()

    # 1. Retrieve today's prompt from soundlog-ai
    today_prompt = Prompt.objects.filter(
        prompt_type='DAILY',
        created_at=today_in_la
    ).last()

    if not today_prompt:
        today_prompt = Prompt.objects.filter(prompt_type='DAILY').order_by('-created_at').first()

    if request.method == "POST":
        form = JournalEntryForm(request.POST, request.FILES)
        if form.is_valid():
            entry = form.save(commit=False)
            entry.author = request.user

            if today_prompt:
                entry.prompt = today_prompt

            if entry.image:
                entry.image = convert_heic_if_needed(entry.image)

            entry.save()

            emotion_ids = request.POST.getlist("emotions")
            entry.emotions.set(emotion_ids)

            analyze_entry.delay(entry.id)

            return redirect("home")
    else:
        form = JournalEntryForm()

    print(f"today prompt: {today_prompt}")
    
    emotions = Emotion.objects.all()
    return render(request, "journal/write.html", {
        "form": form,
        "emotions": emotions,
        "today_prompt": today_prompt
    })

@login_required
def edit_profile_qna(request):
    all_prompts = Prompt.objects.filter(prompt_type='PREFERENCE').distinct()
    
    if request.method == "POST":
        ProfileAnswer.objects.filter(user=request.user).delete()
        
        for i in range(1, 7):
            prompt_id = request.POST.get(f'prompt_slot_{i}')
            answer_text = request.POST.get(f'answer_slot_{i}')
            
            if prompt_id and answer_text:
                prompt = Prompt.objects.get(id=prompt_id)
                ProfileAnswer.objects.create(
                    user=request.user,
                    prompt=prompt,
                    answer_text=answer_text
                )
        return redirect('user_profile', username=request.user.username)

    current_answers = list(ProfileAnswer.objects.filter(user=request.user)[:6])
    
    return render(request, "journal/edit_profile_qna.html", {
        "all_prompts": all_prompts,
        "current_answers": current_answers
    })

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
    profile_answers = ProfileAnswer.objects.filter(user=target_user).select_related('prompt')[:6]

    # check the following status
    is_own_profile = request.user == target_user
    is_following = False
    if request.user.is_authenticated and not is_own_profile:
        is_following = target_user.profile in request.user.profile.following.all()

    context = {
        "target_user": target_user,
        "profile": profile,
        "entries": entries,
        "profile_answers": profile_answers,
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
        return JsonResponse({"error": 'not_authenticated'}, status=403)
    
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

            if updated_entry.image:
                updated_entry.image = convert_heic_if_needed(updated_entry.image)

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

    if notification.entry:
        return redirect("entry_detail", entry_id=notification.entry.id)
    return redirect("home")


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
    return render(request, 'journal/edit_comment.html', {'form': form, 'comment': comment})

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

    # Build seeds/targets
    emotion = (entry.detected_emotion or "").lower().strip()
    seed_genres = (EMOTION_GENRES.get(emotion) or DEFAULT_GENRES)[:3]

    targets = EMOTION_FEATURES.get(emotion, {})
    params = {
        "seed_genres": ",".join(seed_genres),
        "limit": 20,
        "market": "US",  # optionally derive from user locale/profile
        **targets,
    }

    # Cache key (include entry, emotion, seeds, and targets signature)
    targets_sig = ",".join(f"{k}={v}" for k, v in sorted(targets.items()))
    cache_key = f"recs:v1:{entry_id}:{emotion}:{params['seed_genres']}:{targets_sig}"
    cached = cache.get(cache_key)
    if cached:
        logging.getLogger(__name__).info(
            "metric rec_cache hit=True seeds=%s", params['seed_genres']
        )
        return render(request, "journal/_recommendations.html", {"tracks": cached, "query": emotion or "mood"})

    t0 = time.perf_counter()
    err = None
    tracks = []
    try:
        token = spotify_token_manager.get_token()
        if not token:
            return render(request, "journal/_recommendations.html", {"tracks": [], "query": emotion or "mood"})
        headers = {"Authorization": f"Bearer {token}"}

        resp = _session.get(
            "https://api.spotify.com/v1/recommendations",
            headers=headers,
            params=params,
            timeout=(3.05, 5),
        )
        if resp.status_code != 200:
            err = f"recs_{resp.status_code}"
        else:
            items = resp.json().get("tracks", []) or []

            # Normalize + enforce simple artist diversity
            seen_artists = set()
            normalized = []
            for tr in items:
                if not tr or not tr.get("name"):
                    continue
                artist_names = [a["name"] for a in (tr.get("artists") or []) if a.get("name")]
                if not artist_names:
                    continue
                primary_artist = artist_names[0]
                if primary_artist in seen_artists:
                    continue
                seen_artists.add(primary_artist)

                images = (tr.get("album") or {}).get("images") or []
                image = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else None)

                normalized.append({
                    "name": tr["name"],
                    "artist": ", ".join(artist_names),
                    "url": tr["external_urls"]["spotify"],
                    "image": image,
                    "popularity": tr.get("popularity", 0),
                })

                if len(normalized) >= 5:
                    break

            tracks = normalized

            # Fallback if diversity filtered too much
            if len(tracks) < 5 and items:
                for tr in items:
                    if len(tracks) >= 5:
                        break
                    if not tr or not tr.get("name"):
                        continue
                    artist_names = [a["name"] for a in (tr.get("artists") or []) if a.get("name")]
                    images = (tr.get("album") or {}).get("images") or []
                    image = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else None)
                    tracks.append({
                        "name": tr["name"],
                        "artist": ", ".join(artist_names),
                        "url": tr["external_urls"]["spotify"],
                        "image": image,
                        "popularity": tr.get("popularity", 0),
                    })

        # Retry once with relaxed params if we had an error or no tracks
        if (err is not None) or (not tracks):
            relaxed_params = {
                "seed_genres": params["seed_genres"],
                "limit": 20,
                "market": params["market"],
            }
            resp2 = _session.get(
                "https://api.spotify.com/v1/recommendations",
                headers=headers,
                params=relaxed_params,
                timeout=(3.05, 5),
            )
            if resp2.status_code == 200:
                items2 = resp2.json().get("tracks", []) or []
                if items2:
                    err = None
                    tracks = []
                    seen_artists = set()
                    for tr in items2:
                        if len(tracks) >= 5:
                            break
                        if not tr or not tr.get("name"):
                            continue
                        artist_names = [a["name"] for a in (tr.get("artists") or []) if a.get("name")]
                        if not artist_names:
                            continue
                        primary_artist = artist_names[0]
                        if primary_artist in seen_artists:
                            continue
                        seen_artists.add(primary_artist)
                        images = (tr.get("album") or {}).get("images") or []
                        image = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else None)
                        tracks.append({
                            "name": tr["name"],
                            "artist": ", ".join(artist_names),
                            "url": tr["external_urls"]["spotify"],
                            "image": image,
                            "popularity": tr.get("popularity", 0),
                        })
            else:
                err = err or f"recs_relaxed_{resp2.status_code}"

        # Final fallback to old playlist flow if still empty
        if not tracks:
            search_resp = _session.get(
                "https://api.spotify.com/v1/search",
                headers=headers,
                params={"q": f"{emotion or 'chill'} playlist", "type": "playlist", "limit": 5, "market": params["market"]},
                timeout=(3.05, 5),
            )
            if search_resp.status_code == 200:
                playlists = (search_resp.json().get("playlists") or {}).get("items", [])
                if playlists and len(playlists) > 0:
                    valid_playlists = [p for p in playlists if p is not None]
                    if valid_playlists:
                        top_playlist_id = valid_playlists[0]["id"]
                    tr_resp = _session.get(
                        f"https://api.spotify.com/v1/playlists/{top_playlist_id}/tracks",
                        headers=headers,
                        params={"market": params["market"]},
                        timeout=(3.05, 5),
                    )
                    if tr_resp.status_code == 200:
                        items3 = tr_resp.json().get("items", [])
                        all_tracks = [
                            {
                                "name": it["track"]["name"],
                                "artist": ", ".join(a["name"] for a in (it["track"].get("artists") or []) if a.get("name")),
                                "url": it["track"]["external_urls"]["spotify"],
                                "image": (
                                    it["track"]["album"]["images"][1]["url"]
                                    if it["track"].get("album") and it["track"]["album"].get("images")
                                    else None
                                ),
                                "popularity": it["track"].get("popularity", 0),
                            }
                            for it in items3
                            if it.get("track") and it["track"].get("name")
                        ]
                        all_tracks.sort(key=lambda x: x["popularity"], reverse=True)
                        tracks = all_tracks[:5]
    finally:
        latency_ms = (time.perf_counter() - t0) * 1000
        logging.getLogger(__name__).info(
            "metric rec_view latency_ms=%.1f error=%s seeds=%s", latency_ms, err, ",".join(seed_genres)
        )

    # Cache the result
    if tracks:
        cache.set(cache_key, tracks, timeout=60 * 60 * 12)  # 12 hours
        logging.getLogger(__name__).info("metric rec_cache hit=False seeds=%s", params['seed_genres'])

    return render(request, "journal/_recommendations.html", {"tracks": tracks, "query": emotion or "mood"})


@login_required
def add_daily_record(request):
    today = now().date()
    existing_record = DailyRecord.objects.filter(
        user=request.user,
        date=today
    ).first()

    if existing_record:
        return redirect('view_daily_record', record_id=existing_record.id)

    if request.method == 'POST':
        form = DailyRecordForm(request.POST, request.FILES)
        if form.is_valid():
            daily_record = form.save(commit=False)
            daily_record.user = request.user
            daily_record.date = today
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


@login_required
def edit_daily_record(request, record_id):
    record = get_object_or_404(DailyRecord, id=record_id, user=request.user)
    
    if request.method == 'POST':
        form = DailyRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            return redirect('view_daily_record', record_id=record.id)
    else:
        form = DailyRecordForm(instance=record)
    
    emotions = Emotion.objects.all()
    return render(request, 'journal/edit_daily_record.html', {
        'form': form,
        'record': record,
        'emotions': emotions,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY
    })


@login_required
def prompt_feed(request):
    user_tz = pytz.timezone('America/Los_Angeles')
    today_in_la = timezone.now().astimezone(user_tz).date()

    today_prompt = Prompt.objects.filter(
        prompt_type='DAILY',
        created_at=today_in_la
    ).last()

    if not today_prompt:
        today_prompt = Prompt.objects.filter(prompt_type='DAILY').order_by('-created_at').first()

    entries = JournalEntry.objects.filter(
        prompt=today_prompt
    ).select_related('author').prefetch_related('emotions', 'likes').order_by('-created_at') if today_prompt else []

    return render(request, "journal/prompt_feed.html", {
        "today_prompt": today_prompt,
        "entries": entries,
        "entry_count": len(entries) if isinstance(entries, list) else entries.count(),
    })


@login_required
def view_today_song(request):
    today = now().date()
    record = DailyRecord.objects.filter(user=request.user, date=today).first()


    if record:
        return render(request, "journal/view_daily_record.html", {"record": record})
    else:
        return redirect("add_daily_record")
