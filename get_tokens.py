"""
PlaysSync — One-time setup script
Run this once locally to generate your GitHub Actions secrets.

Usage:
    pip install spotipy ytmusicapi
    python get_tokens.py
"""

import json
import re
import sys
import webbrowser
import http.server
import urllib.parse
import threading
import base64
import os
import requests

REDIRECT_URI = "http://127.0.0.1:8080"
SCOPE        = "playlist-read-private playlist-modify-private playlist-modify-public"


def banner():
    print()
    print("╔═══════════════════════════════════════╗")
    print("║          PlaysSync  ♫                 ║")
    print("║        One-Time Setup                 ║")
    print("╚═══════════════════════════════════════╝")
    print()


def step(n: int, title: str):
    print(f"\n{'─'*45}")
    print(f"  Step {n}: {title}")
    print(f"{'─'*45}\n")


# ── Spotify ───────────────────────────────────────────────────────────────────

def setup_spotify():
    step(1, "Spotify Developer App")
    print("  1. Go to https://developer.spotify.com/dashboard")
    print("  2. Click Create App")
    print("  3. Set Redirect URI →  http://127.0.0.1:8080")
    print("  4. Check Web API → Save")
    print()

    client_id     = input("  Paste Client ID     : ").strip()
    client_secret = input("  Paste Client Secret : ").strip()
    print()

    # Build auth URL
    params = urllib.parse.urlencode({
        "client_id":     client_id,
        "response_type": "code",
        "redirect_uri":  REDIRECT_URI,
        "scope":         SCOPE,
    })
    auth_url = f"https://accounts.spotify.com/authorize?{params}"

    # Catch the OAuth callback with a local server
    auth_code_holder = []

    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            code   = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]
            if code:
                auth_code_holder.append(code)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h2 style='font-family:sans-serif'>Got it! You can close this tab.</h2>")

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 8080), _Handler)
    t = threading.Thread(target=server.handle_request)
    t.start()

    print("  Opening Spotify login in your browser...")
    webbrowser.open(auth_url)
    t.join(timeout=120)

    if not auth_code_holder:
        print("\n  ❌ Timed out. Run the script again.")
        sys.exit(1)

    # Exchange code for refresh token
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    token_resp = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {creds}"},
        data={
            "grant_type":   "authorization_code",
            "code":         auth_code_holder[0],
            "redirect_uri": REDIRECT_URI,
        },
    ).json()

    if "refresh_token" not in token_resp:
        print(f"\n  ❌ Token exchange failed: {token_resp}")
        sys.exit(1)

    print("  ✅ Spotify authenticated!\n")
    return client_id, client_secret, token_resp["refresh_token"]


# ── YT Music ──────────────────────────────────────────────────────────────────

def setup_ytmusic() -> str:
    step(2, "YouTube Music Headers")
    print("  1. Open https://music.youtube.com in your browser")
    print("  2. Press F12  →  Network tab")
    print("  3. Type 'browse' in the filter box")
    print("  4. Click on any result going to music.youtube.com")
    print("  5. Right-click  →  Copy  →  Copy as cURL (bash)")
    print("  6. Paste the ENTIRE curl command below, then press Ctrl-D")
    print()

    curl_text = sys.stdin.read()

    # Parse -H 'Key: Value' pairs directly (bypasses ytmusicapi parser issues)
    headers = {}
    for m in re.finditer(r"-H '([^']+?)'", curl_text):
        raw = m.group(1)
        if ':' in raw:
            k, v = raw.split(':', 1)
            headers[k.strip()] = v.strip()

    required = {"cookie", "x-goog-authuser"}
    found    = {k.lower() for k in headers}
    missing  = required - found

    if missing:
        print(f"\n  ❌ Missing headers: {missing}")
        print("     Make sure you copied a /browse request and are logged in.")
        sys.exit(1)

    result = json.dumps(headers, indent=2)
    print("\n  ✅ YouTube Music authenticated!\n")
    return result


# ── Print secrets ─────────────────────────────────────────────────────────────

def print_secrets(client_id, client_secret, refresh_token, ytm_json):
    print()
    print("╔═══════════════════════════════════════════════════════╗")
    print("║   Add these 4 secrets to your GitHub repo:           ║")
    print("║   Settings → Secrets → Actions → New secret          ║")
    print("╚═══════════════════════════════════════════════════════╝")

    secrets = [
        ("SPOTIFY_CLIENT_ID",     client_id),
        ("SPOTIFY_CLIENT_SECRET", client_secret),
        ("SPOTIFY_REFRESH_TOKEN", refresh_token),
        ("YTMUSIC_OAUTH_JSON",    ytm_json),
    ]

    for name, value in secrets:
        print(f"\n  Secret name:  {name}")
        print(f"  Secret value: {value}")

    print()
    print("─" * 55)
    print("  After adding secrets, enable Actions in your repo.")
    print("  First sync runs immediately. Then every 6 hours.")
    print("─" * 55)
    print()


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    banner()
    client_id, client_secret, refresh_token = setup_spotify()
    ytm_json = setup_ytmusic()
    print_secrets(client_id, client_secret, refresh_token, ytm_json)
