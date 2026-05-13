from celery import shared_task
from transformers import pipeline, AutoTokenizer
from keybert import KeyBERT
from .models import JournalEntry
from django.core.cache import cache
from django.conf import settings
import requests
from .constants import EMOTION_GENRES, EMOTION_FEATURES, DEFAULT_GENRES
from .utils.spotify import SpotifyTokenManager
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ✅ 모델 & 토크나이저 로딩
tokenizer = AutoTokenizer.from_pretrained("j-hartmann/emotion-english-distilroberta-base")
classifier = pipeline(
    "text-classification",
    model="j-hartmann/emotion-english-distilroberta-base",
    top_k=None
)
kw_model = KeyBERT()

_session = requests.Session()
_retries = Retry(total=3, backoff_factor=0.3, status_forcelist=[429,500,502,503,504], allowed_methods=["GET"], raise_on_status=False)
_adapter = HTTPAdapter(max_retries=_retries, pool_connections=10, pool_maxsize=10)
_session.mount("https://", _adapter)
_session.mount("http://", _adapter)
_spotify = SpotifyTokenManager(settings.SPOTIFY_CLIENT_ID, settings.SPOTIFY_CLIENT_SECRET)

@shared_task
def analyze_entry(entry_id):
    entry = JournalEntry.objects.get(id=entry_id)
    text = entry.content

    # ✅ 토큰화 + truncate
    tokens = tokenizer(text, truncation=True, max_length=512)
    truncated_text = tokenizer.decode(tokens["input_ids"], skip_special_tokens=True)

    # ✅ 감정 분석 (pipeline에는 string만 넘김!)
    results = classifier(truncated_text)
    results = results[0]
    top = max(results, key=lambda x: x["score"])
    raw_label = top["label"].lower()

    # ✅ 키워드 추출
    keywords = [kw for kw, score in kw_model.extract_keywords(text, top_n=5)]

    entry.detected_emotion = raw_label
    entry.detected_keywords = keywords
    entry.save(update_fields=["detected_emotion", "detected_keywords"])

    # Prefetch recommendations into cache
    prefetch_recommendations.delay(entry_id)


@shared_task
def prefetch_recommendations(entry_id):
    try:
        entry = JournalEntry.objects.get(id=entry_id)
    except JournalEntry.DoesNotExist:
        return

    emotion = (entry.detected_emotion or "").lower().strip()
    seed_genres = (EMOTION_GENRES.get(emotion) or DEFAULT_GENRES)[:3]
    targets = EMOTION_FEATURES.get(emotion, {})
    params = {
        "seed_genres": ",".join(seed_genres),
        "limit": 20,
        "market": "US",
        **targets,
    }

    targets_sig = ",".join(f"{k}={v}" for k, v in sorted(targets.items()))
    cache_key = f"recs:v1:{entry_id}:{emotion}:{params['seed_genres']}:{targets_sig}"
    if cache.get(cache_key):
        return

    token = _spotify.get_token()
    headers = {"Authorization": f"Bearer {token}"}
    tracks = []

    # Try recommendations
    resp = _session.get("https://api.spotify.com/v1/recommendations", headers=headers, params=params, timeout=(3.05,5))
    if resp.status_code == 200:
        items = resp.json().get("tracks", []) or []
        seen = set()
        for tr in items:
            if len(tracks) >= 5:
                break
            if not tr or not tr.get("name"):
                continue
            artist_names = [a["name"] for a in (tr.get("artists") or []) if a.get("name")]
            if not artist_names:
                continue
            if artist_names[0] in seen:
                continue
            seen.add(artist_names[0])
            images = (tr.get("album") or {}).get("images") or []
            image = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else None)
            tracks.append({
                "name": tr["name"],
                "artist": ", ".join(artist_names),
                "url": tr["external_urls"]["spotify"],
                "image": image,
                "popularity": tr.get("popularity", 0),
            })

    # Relaxed retry
    if not tracks:
        relaxed = {"seed_genres": params["seed_genres"], "limit": 20, "market": params["market"]}
        resp2 = _session.get("https://api.spotify.com/v1/recommendations", headers=headers, params=relaxed, timeout=(3.05,5))
        if resp2.status_code == 200:
            items2 = resp2.json().get("tracks", []) or []
            seen = set()
            for tr in items2:
                if len(tracks) >= 5:
                    break
                if not tr or not tr.get("name"):
                    continue
                artist_names = [a["name"] for a in (tr.get("artists") or []) if a.get("name")]
                if not artist_names:
                    continue
                if artist_names[0] in seen:
                    continue
                seen.add(artist_names[0])
                images = (tr.get("album") or {}).get("images") or []
                image = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else None)
                tracks.append({
                    "name": tr["name"],
                    "artist": ", ".join(artist_names),
                    "url": tr["external_urls"]["spotify"],
                    "image": image,
                    "popularity": tr.get("popularity", 0),
                })

    # Fallback to playlist
    if not tracks:
        search_resp = _session.get(
            "https://api.spotify.com/v1/search", headers=headers,
            params={"q": f"{emotion or 'chill'} playlist", "type": "playlist", "limit": 5, "market": "US"}, timeout=(3.05,5)
        )
        if search_resp.status_code == 200:
            res_data = search_resp.json().get("playlists") or {}
            items = res_data.get("items") or []

            valid_items = [item for item in items if item is not None]

            if valid_items:
                pid = valid_items[0].get("id")

                if pid:   
                    tr_resp = _session.get(f"https://api.spotify.com/v1/playlists/{pid}/tracks", headers=headers, params={"market": "US"}, timeout=(3.05,5))
                    if tr_resp.status_code == 200:
                        items3 = tr_resp.json().get("items", [])
                        for it in items3[:5]:
                            if not it.get("track") or not it["track"].get("name"):
                                continue
                            artist_names = [a["name"] for a in (it["track"].get("artists") or []) if a.get("name")]
                            images = (it["track"].get("album") or {}).get("images") or []
                            image = images[1]["url"] if len(images) > 1 else (images[0]["url"] if images else None)
                            tracks.append({
                                "name": it["track"]["name"],
                                "artist": ", ".join(artist_names),
                                "url": it["track"]["external_urls"]["spotify"],
                                "image": image,
                                "popularity": it["track"].get("popularity", 0),
                            })

    if tracks:
        cache.set(cache_key, tracks, timeout=60*60*12)
