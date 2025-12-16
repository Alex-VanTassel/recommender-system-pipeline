from auth import *
import time
from pathlib import Path
import requests
from base64 import b64encode

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
        print("Refresh successful")

    def is_token_expired(self, buffer=10):
        return self.expires_at < time.time() + buffer


    def request(self, method, endpoint, params=None, data=None, json_data=None):
        """
        Make a request to the Spotify API, handling token refresh automatically.

        Args:
            method: 'GET', 'POST', etc.
            endpoint: Spotify API endpoint, e.g., '/v1/me/top/tracks'
            params: dict of query parameters
            data: dict for form-encoded body
            json_data: dict for JSON body

        Returns:
            Parsed JSON response from Spotify
        """
        # Refresh token if expired
        if self.is_token_expired():
            self.refresh_access_token()

        # Construct full URL
        base_url = "https://api.spotify.com"
        url = f"{base_url}{endpoint}"

        # Add authorization header
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        # Make request
        response = requests.request(method, url, headers=headers, params=params, data=data, json=json_data)

        # 5. Error handling
        if response.status_code >= 400:
            raise RuntimeError(f"Spotify API request failed [{response.status_code}]: {response.text}")

        # 6. Return parsed JSON
        return response.json()

    def get_current_user_profile(self):
        return self.request('GET', '/v1/me')

    def get_user_playlists(self):
        params = {
            'limit': 10,
            'offset': 5
        }
        return self.request('GET', '/v1/me/playlists', params=params)

    def get_playlist_tracks(self):
        pass

    def get_user_top_tracks(self):
        pass

    def get_audio_features(self):
        pass

    def paginate(self):
        pass

    def validate_token(self):
        pass