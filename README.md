# 🎵 Soundlog

**Soundlog** is a full-stack social journaling web application that lets users express emotions through journal entries and music.  
Users can share their moods, discover songs that resonate with them, and interact with friends through comments, likes, and follows.

🌐 [Live Demo](http://3.135.241.17/)

---

## ✨ Features

- ✍️ Create journal entries with a title, content, emotion tag, image, and optional song with lyric snippets
- 🎧 Search for songs via the Spotify API and embed a preview player
- 💬 Comment on entries and optionally recommend songs
- ❤️ Like and 🔄 follow other users; both buttons work instantly via AJAX
- 🎨 Journal background color changes based on the selected emotion
- 🔍 Search for users and view profiles with their entries
- 🧾 Personal "My Page" where users can edit or delete only their own entries
- 🔔 Notification system (in progress): see who followed you, commented, or liked your entry

---

## 🎥 Demo Videos
- Sign Up / Logout / Login

https://github.com/user-attachments/assets/4490532b-2f19-4041-a542-84bba7f4aaf9


- Write a Journal Entry

https://github.com/user-attachments/assets/aec6205b-3f7b-44eb-bfa7-4c421ad24ec8


- Like and Comment on a Journal Entry

https://github.com/user-attachments/assets/948c976c-637c-4a00-babe-13c230551b12


- Check Notification

https://github.com/user-attachments/assets/c6150123-57a7-4596-ad54-b8f9515e698a

https://github.com/user-attachments/assets/8c71a4a0-030a-43cd-8c3b-abcee125677b

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
- AWS EC2 + S3 + Gunicorn + Nginx (deployment)
- GitHub (version control)

---

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
