# 🎵 Soundlog

**Soundlog** is a full-stack social journaling web application that lets users express emotions through journal entries and music.  
Users can share their moods, discover songs that resonate with them, and interact with friends through comments, likes, and follows.

🌐 [Live Demo](https://soundlog-clkk.onrender.com)

---

## ✨ Features

- ✍️ Create journal entries with a title, content, emotion tag, and optional song
- 🎧 Search for songs via the Spotify API and embed a preview player
- 💬 Comment on entries and optionally recommend songs with lyric snippets
- ❤️ Like and 🔄 follow other users; both buttons work instantly via AJAX
- 🎨 Journal background color changes based on the selected emotion
- 🔍 Search for users and view profiles with their entries
- 🧾 Personal "My Page" where users can edit or delete only their own entries
- 🔔 Notification system (in progress): see who followed you, commented, or liked your entry

---

## 🛠 Tech Stack

**Frontend:**
- Tailwind CSS
- AJAX (vanilla JS fetch)

**Backend:**
- Django
- Django REST Framework (for Spotify integration)
- SQLite3 (local) / PostgreSQL (production)

**APIs & Tools:**
- Spotify Web API
- Render (deployment)
- GitHub (version control)

---

## 🚀 Getting Started

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/soundlog.git
   cd soundlog
2. Create and activate a virtual environment:
   python -m venv venv
   source venv/bin/activate
3. Install dependencies:
   pip install -r requirements.txt
4. Add .env file with your credentials:

   DEBUG=True
   SPOTIFY_CLIENT_ID=your_client_id
   SPOTIFY_CLIENT_SECRET=your_client_secret
   ALLOWED_HOSTS=localhost,127.0.0.1
   USE_SQLITE3=True
6. Run migrations and start the server:
   python manage.py migrate
   python manage.py runserver

## 📌 Roadmap

- [x] User authentication (login, signup)
- [x] Emotion tagging and color-coded entries
- [x] Song search & Spotify embed
- [x] Comments with music & lyrics
- [x] Follow, like, and profile pages
- [x] Push notifications
- [ ] Explore page for discovering public entries

## 📄 License

This project is licensed under the MIT License.

## 🙌 Acknowledgements

📄 [Spotify for Developers](https://developer.spotify.com)

📄 [Deploy a Django App on Render](https://render.com/docs/deploy-django)
