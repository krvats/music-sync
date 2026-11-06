# 🎵 Spotify ↔ YT Music Sync

Auto-syncs all playlists bidirectionally every 6 hours via GitHub Actions. Completely free, no monitoring needed.

---

## Setup (one-time, ~5 min)

### 1. Fork this repo
Click **Fork** on GitHub.

### 2. Get your tokens (run once on your PC)

```bash
pip install spotipy ytmusicapi
python get_tokens.py
```

The script will:
- Walk you through creating a free Spotify developer app
- Open your browser for Google login (YT Music)
- Print 4 secrets to paste into GitHub

### 3. Add secrets to GitHub
Go to your forked repo → **Settings → Secrets and variables → Actions → New repository secret**

Add all 4 secrets the script printed:
- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_REFRESH_TOKEN`
- `YTMUSIC_OAUTH_JSON`

### 4. Enable Actions
Go to the **Actions** tab in your fork → click **"I understand my workflows, enable them"**

That's it. ✅

---

## How it works

| Thing | Detail |
|-------|--------|
| Runs every | 6 hours (or manually via Actions tab) |
| Direction | Both ways — Spotify → YTM and YTM → Spotify |
| New playlists | Auto-created on the other service |
| Duplicate prevention | `sync_state.json` tracks what's already been synced |
| Loop prevention | Playlists created by this tool are skipped in the reverse direction |
| Match method | Fuzzy title + artist matching (75% similarity threshold) |
| Tracks not found | Logged in Actions output, skipped gracefully |

---

## Manual sync
Actions tab → **Music Sync** → **Run workflow**

## Logs
Actions tab → click any run → `sync` job → see exactly what was added or missed.

---

## Notes
- Spotify's API only allows adding to playlists you own. Followed playlists are synced read-only (tracks copied to YTM, but no new Spotify playlist is created for them).
- YTMusic OAuth tokens expire after ~6 months. Re-run `get_tokens.py` and update the `YTMUSIC_OAUTH_JSON` secret when that happens.
