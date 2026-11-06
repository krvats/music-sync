"""
PlaysSync — Bidirectional Spotify <-> YouTube Music sync
Runs via GitHub Actions every 6 hours.
State is tracked in sync_state.json (committed to repo).

https://github.com/YOUR_USERNAME/music-sync
"""

import os
import json
import time
import requests
from difflib import SequenceMatcher
import spotipy
from ytmusicapi import YTMusic
from config import (
    SIMILARITY_THRESHOLD,
    REQUEST_DELAY,
    MAX_PLAYLISTS,
    SPOTIFY_PLAYLIST_DESC,
    YTM_PLAYLIST_DESC,
)

STATE_FILE = "sync_state.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def log(symbol: str, message: str, indent: int = 0):
    prefix = "  " * indent
    print(f"{prefix}{symbol} {message}")


def similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio() >= SIMILARITY_THRESHOLD


# ── Auth ──────────────────────────────────────────────────────────────────────

def get_spotify() -> spotipy.Spotify:
    token_data = requests.post(
        "https://accounts.spotify.com/api/token",
        data={
            "grant_type":    "refresh_token",
            "refresh_token": os.environ["SPOTIFY_REFRESH_TOKEN"],
            "client_id":     os.environ["SPOTIFY_CLIENT_ID"],
            "client_secret": os.environ["SPOTIFY_CLIENT_SECRET"],
        },
    ).json()
    if "access_token" not in token_data:
        raise RuntimeError(f"Spotify auth failed: {token_data}")
    return spotipy.Spotify(auth=token_data["access_token"])


def get_ytm() -> YTMusic:
    browser_data = json.loads(os.environ["YTMUSIC_OAUTH_JSON"])
    path = "/tmp/ytm_browser.json"
    with open(path, "w") as f:
        json.dump(browser_data, f)
    return YTMusic(path)


# ── State ─────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {
        "s_to_y":      {},   # spotify_pl_id -> {ytm_id, synced: [sp_track_ids]}
        "y_to_s":      {},   # ytm_pl_id    -> {spotify_id, synced: [video_ids]}
        "ytm_created": [],   # YTM playlist IDs we created (skip in reverse sync)
        "sp_created":  [],   # Spotify playlist IDs we created (skip in reverse sync)
    }


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Spotify helpers ───────────────────────────────────────────────────────────

def sp_get_all_playlists(sp: spotipy.Spotify) -> list:
    items, results = [], sp.current_user_playlists(limit=MAX_PLAYLISTS)
    while results:
        items.extend(results["items"])
        results = sp.next(results) if results["next"] else None
    return items


def sp_get_tracks(sp: spotipy.Spotify, pl_id: str) -> list:
    tracks, results = [], sp.playlist_tracks(pl_id, limit=100)
    while results:
        for item in results["items"]:
            t = item.get("track")
            if t and t.get("id"):
                tracks.append({
                    "id":     t["id"],
                    "title":  t["name"],
                    "artist": t["artists"][0]["name"] if t["artists"] else "",
                })
        results = sp.next(results) if results["next"] else None
    return tracks


def sp_find_track(sp: spotipy.Spotify, title: str, artist: str) -> str | None:
    try:
        q = f"track:{title}"
        if artist:
            q += f" artist:{artist}"
        results = sp.search(q, type="track", limit=5)
        for t in results["tracks"]["items"]:
            t_artist = t["artists"][0]["name"] if t["artists"] else ""
            if similar(t["name"], title) and (not artist or similar(t_artist, artist)):
                return t["id"]
    except Exception as e:
        log("!", f"Spotify search error for '{title}': {e}", indent=1)
    return None


# ── YT Music helpers ──────────────────────────────────────────────────────────

def ytm_get_all_playlists(ytm: YTMusic) -> list:
    return ytm.get_library_playlists(limit=MAX_PLAYLISTS) or []


def ytm_get_tracks(ytm: YTMusic, pl_id: str) -> list:
    result = ytm.get_playlist(pl_id, limit=None)
    tracks = []
    for t in result.get("tracks", []):
        if not t.get("videoId"):
            continue
        artists = t.get("artists") or []
        tracks.append({
            "videoId": t["videoId"],
            "title":   t["title"],
            "artist":  artists[0]["name"] if artists else "",
        })
    return tracks


def ytm_find_track(ytm: YTMusic, title: str, artist: str) -> str | None:
    try:
        results = ytm.search(f"{title} {artist}", filter="songs", limit=5)
        for r in results:
            if r.get("resultType") != "song" or not r.get("videoId"):
                continue
            r_artists = r.get("artists") or []
            r_artist  = r_artists[0]["name"] if r_artists else ""
            if similar(r["title"], title) and (not artist or similar(r_artist, artist)):
                return r["videoId"]
    except Exception as e:
        log("!", f"YTM search error for '{title}': {e}", indent=1)
    return None


# ── Sync: Spotify → YT Music ──────────────────────────────────────────────────

def sync_spotify_to_ytm(sp: spotipy.Spotify, ytm: YTMusic, state: dict):
    print()
    print("┌─────────────────────────────┐")
    print("│   Spotify  →  YT Music      │")
    print("└─────────────────────────────┘")

    s_to_y       = state["s_to_y"]
    skip_ytm_ids = set(state.get("ytm_created", []))
    added_total  = 0
    missed_total = 0

    for pl in sp_get_all_playlists(sp):
        pl_id, pl_name = pl["id"], pl["name"]
        print(f"\n  ▶  {pl_name}")

        if pl_id not in s_to_y:
            s_to_y[pl_id] = {"name": pl_name, "ytm_id": None, "synced": []}

        # Find or create matching YTM playlist
        ytm_id = s_to_y[pl_id].get("ytm_id")
        if not ytm_id:
            for ypl in ytm_get_all_playlists(ytm):
                if ypl["title"].lower() == pl_name.lower() and ypl["playlistId"] not in skip_ytm_ids:
                    ytm_id = ypl["playlistId"]
                    break
            if not ytm_id:
                ytm_id = ytm.create_playlist(pl_name, YTM_PLAYLIST_DESC)
                state.setdefault("ytm_created", []).append(ytm_id)
                log("✚", "Created playlist on YT Music", indent=2)
            s_to_y[pl_id]["ytm_id"] = ytm_id

        already   = set(s_to_y[pl_id]["synced"])
        new_vids  = []
        missed    = []

        for track in sp_get_tracks(sp, pl_id):
            if track["id"] in already:
                continue
            vid = ytm_find_track(ytm, track["title"], track["artist"])
            if vid:
                new_vids.append(vid)
                already.add(track["id"])
                log("+", f"{track['title']} — {track['artist']}", indent=2)
            else:
                missed.append(f"{track['title']} — {track['artist']}")
                log("✗", f"{track['title']} — {track['artist']} (not found)", indent=2)
            time.sleep(REQUEST_DELAY)

        if new_vids:
            ytm.add_playlist_items(ytm_id, new_vids)
            log("→", f"Added {len(new_vids)} track(s) to YT Music", indent=2)

        added_total  += len(new_vids)
        missed_total += len(missed)
        s_to_y[pl_id]["synced"] = list(already)

    state["s_to_y"] = s_to_y
    print(f"\n  Summary: {added_total} added, {missed_total} not found")


# ── Sync: YT Music → Spotify ──────────────────────────────────────────────────

def sync_ytm_to_spotify(sp: spotipy.Spotify, ytm: YTMusic, state: dict):
    print()
    print("┌─────────────────────────────┐")
    print("│   YT Music  →  Spotify      │")
    print("└─────────────────────────────┘")

    y_to_s       = state["y_to_s"]
    skip_ytm_ids = set(state.get("ytm_created", []))
    skip_sp_ids  = set(state.get("sp_created",  []))
    sp_user_id   = sp.current_user()["id"]
    added_total  = 0
    missed_total = 0

    for pl in ytm_get_all_playlists(ytm):
        ytm_id, pl_name = pl["playlistId"], pl["title"]

        if ytm_id in skip_ytm_ids:
            print(f"\n  ⊘  {pl_name} (created by this sync, skipping)")
            continue

        print(f"\n  ▶  {pl_name}")

        if ytm_id not in y_to_s:
            y_to_s[ytm_id] = {"name": pl_name, "spotify_id": None, "synced": []}

        sp_id = y_to_s[ytm_id].get("spotify_id")
        if not sp_id:
            for spl in sp_get_all_playlists(sp):
                if spl["name"].lower() == pl_name.lower() and spl["id"] not in skip_sp_ids:
                    sp_id = spl["id"]
                    break
            if not sp_id:
                result = sp.user_playlist_create(
                    sp_user_id, pl_name,
                    public=False,
                    description=SPOTIFY_PLAYLIST_DESC,
                )
                sp_id = result["id"]
                state.setdefault("sp_created", []).append(sp_id)
                log("✚", "Created playlist on Spotify", indent=2)
            y_to_s[ytm_id]["spotify_id"] = sp_id

        already         = set(y_to_s[ytm_id]["synced"])
        new_track_uris  = []
        missed          = []

        for track in ytm_get_tracks(ytm, ytm_id):
            if track["videoId"] in already:
                continue
            sp_track_id = sp_find_track(sp, track["title"], track["artist"])
            if sp_track_id:
                new_track_uris.append(f"spotify:track:{sp_track_id}")
                already.add(track["videoId"])
                log("+", f"{track['title']} — {track['artist']}", indent=2)
            else:
                missed.append(f"{track['title']} — {track['artist']}")
                log("✗", f"{track['title']} — {track['artist']} (not found)", indent=2)
            time.sleep(REQUEST_DELAY)

        # Spotify caps add at 100 tracks per call
        for i in range(0, len(new_track_uris), 100):
            sp.playlist_add_items(sp_id, new_track_uris[i:i + 100])

        if new_track_uris:
            log("→", f"Added {len(new_track_uris)} track(s) to Spotify", indent=2)

        added_total  += len(new_track_uris)
        missed_total += len(missed)
        y_to_s[ytm_id]["synced"] = list(already)

    state["y_to_s"] = y_to_s
    print(f"\n  Summary: {added_total} added, {missed_total} not found")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("╔═══════════════════════════════════════╗")
    print("║          PlaysSync  ♫                 ║")
    print("║   Spotify  ⟷  YouTube Music           ║")
    print("╚═══════════════════════════════════════╝")

    print("\nAuthenticating...")
    sp  = get_spotify()
    ytm = get_ytm()
    print("✓ Spotify")
    print("✓ YouTube Music")

    state = load_state()

    sync_spotify_to_ytm(sp, ytm, state)
    sync_ytm_to_spotify(sp, ytm, state)

    save_state(state)
    print("\n✅ Sync complete.\n")


if __name__ == "__main__":
    main()
