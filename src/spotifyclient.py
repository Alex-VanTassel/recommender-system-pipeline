import time
from pathlib import Path
import requests
from base64 import b64encode
import json

class SpotifyClient:
    def __init__(self, client_id, client_secret, redirect_uri, tokens_file="tokens.json"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.tokens_file = tokens_file

        self.access_token = None
        self.refresh_token = None
        self.expires_at = None
        self._load_tokens()

    def _load_tokens(self):
        '''
        Loads initial tokens from the json file created by running auth.py
        '''
        try:
            with open(self.tokens_file, 'r') as f:
                tokens = json.load(f)
                self.access_token = tokens['access_token']
                self.refresh_token = tokens['refresh_token']

                if "expires_at" in tokens:
                    # New format
                    self.expires_at = tokens["expires_at"]
                elif "expires_in" in tokens:
                    # Old format; compute absolute timestamp
                    self.expires_at = time.time() + tokens["expires_in"]
                else:
                    raise KeyError("Missing 'expires_at' or 'expires_in' in token file.")

        except FileNotFoundError:
            raise RuntimeError("Tokens not found. Please run auth.py to get tokens first.")
        except KeyError as e:
            raise RuntimeError(f"Malformed token file, missing field: {e}")
        
    def save_tokens(self):
        '''
        Writes current access/refresh tokens to json file for secure storage
        '''
        
        data = {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at
        }

        try:
            Path(self.tokens_file).parent.mkdir(parents=True, exist_ok=True)

            with open(self.tokens_file, "w") as f:
                json.dump(data, f, indent=4)
        except (OSError, TypeError) as e:
            raise RuntimeError(f"Unable to save tokens: {e}")
        
    def refresh_access_token(self):
        """
        Refreshes the Spotify access token using the stored refresh token.
        Updates the object's access_token and expires_at fields, and saves them to the JSON file.
        """
        if not self.refresh_token:
            raise RuntimeError("No refresh token available. Run auth.py to generate tokens first.")

        # Prepare authorization header (client_id:client_secret base64)
        auth_str = f"{self.client_id}:{self.client_secret}"
        b64_auth_str = b64encode(auth_str.encode()).decode()
        headers = {
            "Authorization": f"Basic {b64_auth_str}",
            "Content-Type": "application/x-www-form-urlencoded"
        }

        # Prepare payload
        data = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }

        # Make request to Spotify API
        response = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
        tokens = response.json()

        if "error" in tokens:
            raise RuntimeError(f"Failed to refresh token: {tokens}")

        # Update fields
        self.access_token = tokens["access_token"]
        # Note: Spotify may or may not return a new refresh_token; keep existing if missing
        if "refresh_token" in tokens:
            self.refresh_token = tokens["refresh_token"]
        # Compute absolute expiration timestamp
        self.expires_at = time.time() + tokens["expires_in"]

        # Persist updated tokens
        self.save_tokens()

    def is_token_expired(self, buffer=10):
        '''
        Checks to see if access token has expired (or is close to)
        '''
        return self.expires_at < time.time() + buffer


    def request(self, method, endpoint, params=None, data=None, json_data=None):
        base_url = "https://api.spotify.com"
        url = f"{base_url}{endpoint}"

        def _make_request():
            headers = {
                "Authorization": f"Bearer {self.access_token}"
            }
            return requests.request(
                method,
                url,
                headers=headers,
                params=params,
                data=data,
                json=json_data
            )

        # First attempt
        if self.is_token_expired():
            self.refresh_access_token()

        response = _make_request()

        # If token expired anyway, refresh and retry ONCE
        if response.status_code == 401:
            self.refresh_access_token()
            response = _make_request()

        if response.status_code >= 400:
            raise RuntimeError(
                f"Spotify API request failed [{response.status_code}]: {response.text}"
            )

        return response.json()

    def get_current_user_profile(self):
        '''
        Gets the current users profile data
        '''
        return self.request('GET', '/v1/me')

    def get_user_playlists(self):
        '''
        Get's the current users playlists
        '''
        params = {
            'limit': 50
        }
        return self.paginate('/v1/me/playlists', params=params)

    def get_playlist_tracks(self, playlist_id):
        '''
        Gets the tracks belonging to a certain playlist

        Args:
            playlist_id: (str) the ID associated with the playlist

        Returns:
            Dict of users playlists
        '''
        params = {
            'limit': 50
        }

        return self.paginate(f'/v1/playlists/{playlist_id}/tracks', params=params)

    def get_user_top_tracks(self):
        '''
        Returns the users most played songs
        '''
        return self.paginate('/v1/me/top/tracks')

    def get_audio_features(self, song_id):
        '''
        Returns the audio features of a song (song identified through its)
        '''
        return self.request('GET', f'/v1/audio-features/{song_id}')

    def paginate(self, endpoint, params=None):
        items = []
        url = endpoint
        current_params = params

        while url:
            response = self.request('GET', url, params=current_params)

            if 'items' not in response:
                raise RuntimeError("Attempted to paginate a non-paginated endpoint")
            
            items.extend(response.get('items', []))

            url = response.get('next')
            current_params = None

            if url:
                url = url.replace("https://api.spotify.com", "")

        return items