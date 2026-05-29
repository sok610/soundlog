# Soundlog

**Soundlog** is an AI-powered social music journaling platform. Users respond to a daily music-themed prompt, log emotions through journal entries and Spotify tracks, and receive personalized song recommendations driven by NLP emotion classification.

🌐 [Live Demo](http://13.57.23.214) · [soundlog-ai repo](https://github.com/sok610/soundlog-ai)

---

## Architecture

```
soundlog-ai (cron, midnight PST)
    └── Gemini API → generates daily prompt → PostgreSQL

User writes entry
    └── Celery task (async)
            ├── DistilRoBERTa → detected_emotion
            └── Spotify Recommendations API → Redis cache (12h TTL)

GET /entry/:id/recommendations/
    └── cache hit  → ~22ms
        cache miss → Spotify API → normalize → cache → ~4.7s
```

**Stack:**
- **Backend:** Django 4.2, Celery + Redis, PostgreSQL, Gunicorn
- **Frontend:** Tailwind CSS, HTMX, vanilla JS (AJAX)
- **AI / ML:** DistilRoBERTa (Hugging Face), KeyBERT, Gemini API
- **APIs:** Spotify Web API
- **Infra:** AWS EC2 + S3, Nginx, systemd

---

## Features

- **Daily Prompt Feed** — Gemini API generates one music-themed journaling prompt per day; users answer and see how everyone else responded on the Discover page
- **Emotion-Driven Recommendations** — DistilRoBERTa classifies entry text into 7 emotions; Spotify Recommendations API returns tracks seeded by emotion-mapped genres and audio features
- **Performance** — p95 recommendation latency reduced from 4.7s → 0.22s via Redis caching (12h TTL) and Celery pre-warming after entry save
- **Fault Tolerance** — exponential backoff retries, relaxed-param fallback, playlist-search fallback if recommendations API fails
- **Social Layer** — follow/unfollow, likes (AJAX), comments with embedded Spotify players, notifications
- **HEIC Support** — iOS photos auto-converted to JPEG on upload via pillow-heif

---

## Project Structure

```
soundlog/               ← this repo (Django app)
├── journal/
│   ├── models.py       ← JournalEntry, Prompt, Emotion, Profile, ...
│   ├── views.py        ← feed, entry_detail, get_recommendations, prompt_feed, ...
│   ├── tasks.py        ← analyze_entry (Celery), prefetch_recommendations
│   ├── constants.py    ← EMOTION_GENRES, EMOTION_FEATURES, DEFAULT_GENRES
│   └── utils/
│       └── spotify.py  ← SpotifyTokenManager
├── deploy/
│   ├── setup_server.sh ← one-time EC2 bootstrap
│   ├── deploy.sh       ← git pull + migrate + restart
│   ├── soundlog.service
│   ├── soundlog-celery.service
│   └── nginx.conf
└── soundlog/
    └── settings.py

soundlog-ai/            ← separate repo
└── main.py             ← Gemini API → PostgreSQL (runs via cron, midnight PST)
```

---

## Local Setup

```bash
git clone https://github.com/sok610/soundlog.git
cd soundlog

python3 -m venv .venv && source .venv/bin/activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt

cp deploy/.env.stg.template .env  # fill in SPOTIFY_CLIENT_ID, SECRET_KEY, etc.

python manage.py migrate
python manage.py init_emotions
python manage.py runserver
```

**Redis + Celery (for recommendations):**
```bash
redis-server &
celery -A soundlog worker --loglevel=info
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for local, `False` for production |
| `DATABASE_URL` | PostgreSQL connection string |
| `SPOTIFY_CLIENT_ID` | Spotify API client ID |
| `SPOTIFY_CLIENT_SECRET` | Spotify API client secret |
| `CELERY_BROKER_URL` | Redis URL (default: `redis://localhost:6379/0`) |
| `USE_S3` | `True` to serve media from S3 |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | AWS credentials (if `USE_S3=True`) |

---

## Deployment

See [`deploy/setup_server.sh`](deploy/setup_server.sh) for full EC2 bootstrap and [`deploy/deploy.sh`](deploy/deploy.sh) for rolling deploys.

```bash
# On EC2 (first time)
bash deploy/setup_server.sh <soundlog-repo-url> <soundlog-ai-repo-url>

# Subsequent deploys
bash deploy/deploy.sh
```

---

## License

MIT
