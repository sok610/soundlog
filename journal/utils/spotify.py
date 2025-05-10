import requests
import time

class SpotifyTokenManager:
    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        self.expires_at = 0

    def get_token(self):
        if self.access_token is None or time.time() > self.expires_at:
            self.refresh_token()
        return self.access_token
    
    def refresh_token(self):
        response = requests.post(
            "https://accounts.spotify.com/api/token",
            data={"grant_type": "client_credentials"},
            auth=(self.client_id, self.client_secret),
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access_token"]
        self.expires_at = time.time() + data["expires_in"] - 60