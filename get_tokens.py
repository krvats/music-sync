"""
Run this ONCE locally to get your credentials for GitHub Actions.
  pip install spotipy ytmusicapi
  python get_tokens.py
"""

import json
import webbrowser
import http.server
import urllib.parse
import threading
import base64
import requests
import os

REDIRECT_URI = "http://localhost:8080"
SCOPE = "playlist-read-private playlist-modify-private playlist-modify-public"

# ── Spotify ───────────────────────────────────────────────────────────────────

print("=" * 55)
print("  STEP 1: Spotify")
print("=" * 55)
print("""
1. Go to https://developer.spotify.com/dashboard
2. Log in → Create App
3. App name: anything (e.g. 'Music Sync')
4. Redirect URI: http://localhost:8080
5. Check 'Web API' → Save
""")

client_id     = input("Paste your Spotify Client ID     : ").strip()
client_secret = input("Paste your Spotify Client Secret : ").strip()

# Build auth URL
params = urllib.parse.urlencode({
    "client_id": client_id,
    "response_type": "code",
    "redirect_uri": REDIRECT_URI,
    "scope": SCOPE,
})
auth_url = f"https://accounts.spotify.com/authorize?{params}"

# Catch the callback with a tiny local server
auth_code_holder = []

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        code = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]
        if code:
            auth_code_holder.append(code)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"<h2>Got it! You can close this tab.</h2>")

    def log_message(self, *args):
        pass  # silence server logs

server = http.server.HTTPServer(("localhost", 8080), Handler)
t = threading.Thread(target=server.handle_request)
t.start()

print("\nOpening Spotify login in your browser...")
webbrowser.open(auth_url)
t.join(timeout=120)

if not auth_code_holder:
    print("❌ Timed out waiting for Spotify auth. Try again.")
    exit(1)

# Exchange code for tokens
creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
token_resp = requests.post(
    "https://accounts.spotify.com/api/token",
    headers={"Authorization": f"Basic {creds}"},
    data={
        "grant_type": "authorization_code",
        "code": auth_code_holder[0],
        "redirect_uri": REDIRECT_URI,
    },
).json()

if "refresh_token" not in token_resp:
    print(f"❌ Spotify token exchange failed: {token_resp}")
    exit(1)

spotify_refresh_token = token_resp["refresh_token"]
print("✅ Spotify auth done!\n")

# ── YT Music ──────────────────────────────────────────────────────────────────

print("=" * 55)
print("  STEP 2: YT Music")
print("=" * 55)
print("""
Follow the prompts — it will open your browser for Google login.
""")

from ytmusicapi import YTMusic
YTMusic.setup_oauth(filepath="oauth.json", open_browser=True)

with open("oauth.json") as f:
    ytm_oauth = f.read().strip()

os.remove("oauth.json")

# ── Print results ─────────────────────────────────────────────────────────────

print("\n" + "=" * 55)
print("  ADD THESE 4 SECRETS TO GITHUB ACTIONS")
print("  (Repo → Settings → Secrets → Actions → New secret)")
print("=" * 55)
print(f"\nSecret name:  SPOTIFY_CLIENT_ID")
print(f"Secret value: {client_id}")
print(f"\nSecret name:  SPOTIFY_CLIENT_SECRET")
print(f"Secret value: {client_secret}")
print(f"\nSecret name:  SPOTIFY_REFRESH_TOKEN")
print(f"Secret value: {spotify_refresh_token}")
print(f"\nSecret name:  YTMUSIC_OAUTH_JSON")
print(f"Secret value: {ytm_oauth}")
print("\n" + "=" * 55)
print("  Done! Paste each pair into GitHub and you're set.")
print("=" * 55)
