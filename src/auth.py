# NOTE: authentication --> approval --> requesting tokens --> given tokens --> API calls

import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from base64 import b64encode

# ---------- Local HTTP server to catch the auth code ----------
class OAuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        qs = parse_qs(parsed_url.query)
        if "code" in qs:
            self.server.auth_code = qs["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorization received! You can close this tab.</h1>")

server = HTTPServer(("127.0.0.1", 8080), OAuthHandler)

# ---------- Build Spotify auth URL ----------
client_id = "582070c6a93749a1bc3826ac9ad8a32a"
redirect_uri = "http://127.0.0.1:8080/callback"
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
code = server.auth_code
print("Received code:", code)

# ---------- Exchange code for access + refresh tokens ----------
client_secret = "SECRET_KEY"
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

print("Access token:", access_token)
print("Refresh token:", refresh_token)