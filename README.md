<div align="center">

```
╔═══════════════════════════════════════════════╗
║                                               ║
║   ♫  P L A Y S Y N C                         ║
║                                               ║
║   Spotify  ⟷  YouTube Music                  ║
║   Automatic · Bidirectional · Free Forever    ║
║                                               ║
╚═══════════════════════════════════════════════╝
```

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/Runs%20on-GitHub%20Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)
![Cost: Free](https://img.shields.io/badge/Cost-Free-f59e0b?style=flat-square)

**Keep your Spotify and YouTube Music libraries in perfect sync —
automatically, every 6 hours, with zero maintenance.**

[Setup](#setup-5-minutes) · [How It Works](#how-it-works) · [Configuration](#configuration) · [FAQ](#faq)

</div>

---

## Overview

PlaysSync runs entirely on **GitHub Actions** — no server, no VPS, no paid subscription to a sync service. Fork the repo, run a one-time setup script, add 4 secrets, and it handles the rest forever.

```
Your Spotify          GitHub Actions          Your YT Music
─────────────         ──────────────          ─────────────
  Playlist A    ───▶   every 6 hours   ───▶    Playlist A
  Playlist B    ◀───   bidirectional   ◀───    Playlist B
  Playlist C    ───▶     new tracks    ───▶    Playlist C
```

**What it does each run:**
- Finds tracks added to Spotify playlists → copies them to the matching YT Music playlist
- Finds tracks added to YT Music playlists → copies them to the matching Spotify playlist
- Creates the playlist on the other service if it doesn't exist yet
- Skips anything already synced — no duplicates ever
- Commits updated state back to the repo so nothing is synced twice

---

## Requirements

> ⚠️ **Spotify Premium is required.** Spotify's API blocks playlist access for free-tier accounts. This is a Spotify limitation, not a PlaysSync one. Everything else is free.

| Requirement | Notes |
|---|---|
| Spotify Premium account | Required by Spotify's API |
| GitHub account | Free tier is enough |
| YouTube Music account | Any Google account works |
| Python 3.9+ | Only needed once for setup |

---

## Setup (5 minutes)

### 1 · Fork this repo

Click **Fork** at the top right of this page. Keep all defaults and confirm.

---

### 2 · Create a Spotify Developer App

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) and log in
2. Click **Create App**
3. Fill in any name (e.g. `PlaysSync`) and any description
4. Set **Redirect URI** → `http://127.0.0.1:8080`
5. Tick **Web API** under "Which API/SDKs are you planning to use?"
6. Agree to terms → **Save**
7. Click **Settings** on your new app — copy your **Client ID** and **Client Secret**

---

### 3 · Run the setup script (once, on your machine)

```bash
# Install the two dependencies
pip install spotipy ytmusicapi

# Run setup
python get_tokens.py
```

The script will:
1. Ask you to paste your Spotify Client ID and Secret
2. Open your browser for Spotify login
3. Walk you through copying a request header from YouTube Music
4. Print **4 secrets** to paste into GitHub

---

### 4 · Add secrets to GitHub

In your forked repo → **Settings → Secrets and variables → Actions → New repository secret**

Add all 4 (names must be exact):

| Secret | Description |
|---|---|
| `SPOTIFY_CLIENT_ID` | From your Spotify Developer app |
| `SPOTIFY_CLIENT_SECRET` | From your Spotify Developer app |
| `SPOTIFY_REFRESH_TOKEN` | Printed by `get_tokens.py` |
| `YTMUSIC_OAUTH_JSON` | Printed by `get_tokens.py` |

---

### 5 · Enable Actions

Go to the **Actions** tab in your forked repo → click **"I understand my workflows, enable them"**

**That's it.** ✅ The first sync triggers immediately. After that it runs every 6 hours automatically.

---

## How It Works

```
┌──────────────────────────────────────────────────────────┐
│                     sync_state.json                      │
│  Tracks already synced are saved here after every run.   │
│  Committed back to the repo — no database needed.        │
└──────────────────────────────────────────────────────────┘

Loop prevention: playlists created by PlaysSync are tagged
internally. The reverse sync skips them — no echo chamber.

Fuzzy matching: tracks matched by title + artist at 75%
similarity. Handles "feat." vs "ft.", remaster suffixes, etc.
```

**Run logs look like this:**

```
╔═══════════════════════════════════════╗
║          PlaysSync  ♫                 ║
║   Spotify  ⟷  YouTube Music           ║
╚═══════════════════════════════════════╝

Authenticating...
✓ Spotify
✓ YouTube Music

┌─────────────────────────────┐
│   Spotify  →  YT Music      │
└─────────────────────────────┘

  ▶  My Favourites
    + Blinding Lights — The Weeknd
    + Levitating — Dua Lipa
    ✗ Regional Track — Local Artist (not found)
    → Added 2 track(s) to YT Music

  Summary: 2 added, 1 not found

┌─────────────────────────────┐
│   YT Music  →  Spotify      │
└─────────────────────────────┘

  ⊘  My Favourites (created by this sync, skipping)

  ▶  Late Night Drives
    + Redbone — Childish Gambino
    → Added 1 track(s) to Spotify

  Summary: 1 added, 0 not found

✅ Sync complete.
```

---

## Manual Sync

**Actions tab → Music Sync → Run workflow → Run workflow**

---

## Configuration

Edit `config.py` to tune behaviour:

```python
# How closely title + artist must match (0.0 – 1.0)
SIMILARITY_THRESHOLD = 0.75   # lower = more lenient

# Seconds between API search calls
REQUEST_DELAY = 0.4           # increase if you hit rate limits

# Max playlists fetched per service
MAX_PLAYLISTS = 50            # increase if you have more than 50
```

Change sync frequency in `.github/workflows/sync.yml`:

```yaml
- cron: "0 */6 * * *"   # every 6 hours (default)
- cron: "0 */1 * * *"   # every hour
- cron: "0 0 * * *"     # once daily at midnight UTC
```

---

## FAQ

**Will PlaysSync delete tracks I remove?**
No. It only ever adds — it never removes tracks from either platform.

**What about Liked Songs?**
Spotify's API does not expose Liked Songs as a standard playlist, so they are not synced. Only named playlists are.

**My YT Music headers stopped working.**
Browser-based headers expire after a few months. Re-run `get_tokens.py`, copy the new `YTMUSIC_OAUTH_JSON` value, and update it in GitHub Secrets.

**A track synced to the wrong song.**
Fuzzy matching can occasionally mismatch. Lower `SIMILARITY_THRESHOLD` in `config.py` to `0.85` for stricter matching, or raise it to `0.65` to be more lenient.

**Can I sync only some playlists, not all?**
Not natively — it syncs everything. You can add a playlist name filter in `sync.py` by checking `pl_name` against a list before processing.

**The sync is slow.**
Normal — each track requires an API search call with a small delay to avoid rate limits. A 100-track playlist takes about a minute.

---

## File Structure

```
music-sync/
├── sync.py              ← main sync logic (runs in GitHub Actions)
├── get_tokens.py        ← one-time local setup script
├── config.py            ← tunable settings
├── requirements.txt     ← Python dependencies
├── sync_state.json      ← auto-updated after every run
├── .github/
│   └── workflows/
│       └── sync.yml     ← GitHub Actions schedule + job
├── LICENSE
└── .gitignore
```

---

## Tech Stack

| Library | Purpose |
|---|---|
| [spotipy](https://github.com/spotipy-dev/spotipy) | Spotify Web API |
| [ytmusicapi](https://github.com/sigma67/ytmusicapi) | YouTube Music API |
| [GitHub Actions](https://github.com/features/actions) | Free automation scheduler |

---

## License

MIT — do whatever you want with it. Attribution appreciated but not required.

---

<div align="center">
  <sub>Made for people who refuse to pick just one music platform.</sub>
</div>
