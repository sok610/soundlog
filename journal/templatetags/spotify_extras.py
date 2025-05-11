from django import template
import re

register = template.Library()

@register.filter
def extract_track_id(url):
    """
    Extracts Spotify track ID from a URL like:
    https://open.spotify.com/track/{id}?si=...
    or
    https://open.spotify.com/track/{id}
    """
    if not url:
        return ""
    match = re.search(r"spotify\.com/track/([a-zA-Z0-9]+)", url)
    return match.group(1) if match else ""