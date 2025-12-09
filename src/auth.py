import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from base64 import b64encode
import json
import sys

# ---------- Auxillary funciton to read necessary info from file ----------
def load_info(filepath):
    with open(filepath, "r") as f:
        data = json.load(f)
        client_id = data['client_id']
        redirect_uri = data['redirect_uri']
        client_secret = data['client_secret']
        return client_id, redirect_uri, client_secret

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

def start_auth_server(port=8080):
    '''
    Starts a local server to handle Spotify request containing authentication code

    Args:
        port: (int) port from which to host local server

    Returns:
        server: HTTPServer object hosting local server
    '''
    server = HTTPServer(("127.0.0.1", port), OAuthHandler)
    return server 

def retrieve_authentication_code(server, client_id, redirect_uri, scopes):
    '''
    Retrieve authentication code from Spotify by handling get request from spotify sevrer

    Args:
        server: HTTPServer object hosting local server
        client_id: (str) client ID associated with Spotify app
        redirect_uri: (str) redirect uri used to create spotify app
        scopes: (str) scopes for requesting info from spotify API
    '''

    auth_url = (
        f"https://accounts.spotify.com/authorize?client_id={client_id}"
        f"&response_type=code&redirect_uri={redirect_uri}&scope={scopes}"
    )

    webbrowser.open(auth_url)
    server.handle_request()
    auth_code = getattr(server, 'auth_code', None) # Recall that when handling the spotify request we set a server attribute to be the authentication code for retrieval here

    if auth_code is None:
        raise RuntimeError("No authorization code received from Spotify.")
    
    return auth_code

def collect_tokens(client_id, client_secret, redirect_uri, auth_code):
    '''
    Collects access and refresh tokens from Spotify API

    Args:
        client_id: (str) client ID associated with spotify app
        client_secret: (str) client secret associated with spotify app
        redirect_uri: (str) redirect URI associated with spotify app
        auth_code: (str) authentication code from Spotify API

    Returns:
        tokens: Dictionary of key value pairs of the following format: 'token_name': token
    '''
    auth_str = f"{client_id}:{client_secret}"
    b64_auth_str = b64encode(auth_str.encode()).decode()

    data = {
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri
    }

    headers = {
        "Authorization": f"Basic {b64_auth_str}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    resp = requests.post("https://accounts.spotify.com/api/token", headers=headers, data=data)
    tokens = resp.json()
    
    if 'error' in tokens:
        raise ValueError(f"Spotify token request failed: {tokens}")

    return tokens

def store_tokens(filepath, tokens):
    '''
    Stores tokens in a json file located at the filepath

    Args:
        filepath: (str): file path to the json file to store the token info
        tokens: (dct) Dictionary of token info to store in json file
    '''
    with open(filepath, 'w') as f:
        json.dump(tokens, f, indent=4)
        return


def main():

    app_info_file = 'info.json'
    tokens_info_file = 'tokens.json'
    scopes = "user-library-read user-top-read playlist-read-private"

    # ---------- Retrieving environment info from json ----------
    client_id, redirect_uri, client_secret = load_info(app_info_file)

    # ---------- Start local server ----------
    server = start_auth_server(port=8080)

    # ---------- Retrieve access tokens ----------
    print("Waiting for Spotify authorization...")
    auth_code = retrieve_authentication_code(server, client_id, redirect_uri, scopes)

    print("Authorization code received, exchanging for tokens...")
    tokens = collect_tokens(client_id, client_secret, redirect_uri, auth_code)
    

    # ---------- Write access and refresh tokens to json ----------
    tokens_to_store = {
    "access_token": tokens["access_token"],
    "refresh_token": tokens["refresh_token"],
    "expires_in": tokens.get("expires_in")
}
    store_tokens(tokens_info_file, tokens_to_store)
    print("Tokens saved to tokens.json")

if __name__ == '__main__':
    main()