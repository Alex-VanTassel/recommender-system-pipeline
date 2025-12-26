# Script to collect data from Spotify API

from src.spotifyclient import SpotifyClient
from src.auth import load_info

if __name__ == "__main__":
    client_id, redirect_uri, client_secret = load_info('info.json')

    client = SpotifyClient(client_id, client_secret, redirect_uri)

    playlists = client.get_user_playlists()

    playlist_ids = []
    for playlist in playlists:
        playlist_id = playlist['id']
        playlist_name = playlist['name']
        print(f"{playlist_name}")

        if playlist_name in ['Chillin', 'Studying', 'Locked in', 'Latin', 'Slow Vibes', 'Country', 'Feelin some kinda way']:
            playlist_ids.append(playlist_id)

        print(playlist_ids)

