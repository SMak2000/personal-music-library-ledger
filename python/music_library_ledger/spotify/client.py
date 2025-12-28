import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth


def get_spotify_client() -> spotipy.Spotify:
    scopes = os.environ["SPOTIFY_SCOPES"]
    return spotipy.Spotify(
        auth_manager=SpotifyOAuth(
            client_id=os.environ["SPOTIFY_CLIENT_ID"],
            client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
            redirect_uri=os.environ["SPOTIFY_REDIRECT_URI"],
            scope=scopes,
            open_browser=True,
            cache_path=".spotify_token_cache",
        )
    )
