# NOTE: authentication --> approval --> requesting tokens --> given tokens --> API calls

import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from base64 import b64encode
import json
import sys

# ---------- Auxillary funciton to read json file ----------
def load_info():
    with open("info.json", "r") as f:
        return json.load(f)

# ---------- Local HTTP server to catch the auth code ----------
class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        '''
        Handles get requests to the server
        '''
        parsed_url = urlparse(self.path)
        qs = parse_qs(parsed_url.query)
        if "code" in qs:
            self.server.auth_code = qs["code"][0] # Sets a server attribute to be the authentication code
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization received! You can close this tab.</h1>")

server = HTTPServer(("127.0.0.1", 8080), OAuthHandler)

# ---------- Retrieving environment info from json ----------
config = load_info()

client_id = config['client_id']
redirect_uri = config['redirect_uri']
client_secret = config['client_secret']

# ---------- Build Spotify auth URL ----------
scopes = "user-library-read user-top-read playlist-read-private"

auth_url = (
    f"https://accounts.spotify.com/authorize?client_id={client_id}"
    f"&response_type=code&redirect_uri={redirect_uri}&scope={scopes}"
)

# ---------- Open browser automatically ----------
webbrowser.open(auth_url)

# ---------- Wait for code ----------
print("Waiting for authorization...")
server.handle_request()
code = getattr(server, 'auth_code', None)
print("Received code:", code)

# ---------- Exchange code for access + refresh tokens ----------

auth_str = f"{client_id}:{client_secret}"
b64_auth_str = b64encode(auth_str.encode()).decode()

data = {
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": redirect_uri
}

headers = {
    "Authorization": f"Basic {b64_auth_str}",
    "Content-Type": "application/x-www-form-urlencoded"
}

resp = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
tokens = resp.json()
access_token = tokens["access_token"]
refresh_token = tokens["refresh_token"]

# ---------- Write access and refresh tokens to json ----------

token_data = {
    'access_token': access_token,
    'refresh_token': refresh_token
}

with open('tokens.json', 'w') as f:
    json.dump(token_data, f, indent=4)