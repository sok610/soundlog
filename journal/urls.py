from django.urls import path, reverse_lazy
from . import views
from django.contrib.auth import views as auth_views


urlpatterns = [
    # Home
    path("", views.home, name="home"),

    # Authentication
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='journal/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('reset/', auth_views.PasswordResetView.as_view(template_name='journal/password_reset_form.html', email_template_name='journal/password_reset_email.html', success_url=reverse_lazy('password_reset_done')), name='password_reset'),
    path('reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='journal/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='journal/password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='journal/password_reset_complete.html'), name='password_reset_complete'),

    # Journal Functionalities
    path("write/", views.write_entry, name="write_entry"),

    # Social Interaction
    path("user/<str:username>/", views.user_profile, name="user_profile"),
    path("user/<str:username>/following/", views.following_list, name="following_list"),
    path("user/<str:username>/followers/", views.followers_list, name="followers_list"),

    # Spotify-related functions
    path("search-music/", views.search_music, name="search_music"),
    path("search-users/", views.search_users, name="search_users"),

    # UI
    path("follow/<str:username>/", views.toggle_follow, name="toggle_follow"),
    path("like/<int:entry_id>/", views.toggle_like, name="toggle_like"),
    path("like-ajax/<int:entry_id>/", views.toggle_like_ajax, name='toggle_like_ajax'),
    path("follow-ajax/<str:username>/", views.toggle_follow_ajax, name="toggle_follow_ajax"),


    # Entry Functionalities
    path("entry/<int:entry_id>/", views.entry_detail, name="entry_detail"),
    path('entry/<int:entry_id>/edit/', views.edit_entry, name='edit_entry'),
    path('entry/<int:entry_id>/delete/', views.delete_entry, name='delete_entry'),
]