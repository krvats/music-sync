"""
PlaysSync — Configuration
Tweak these to adjust sync behaviour.
"""

# ── Matching ──────────────────────────────────────────────────────────────────

# How similar a title/artist must be to count as a match (0.0 – 1.0)
# Lower = more lenient, may cause false matches
# Higher = stricter, may miss tracks with slightly different names
SIMILARITY_THRESHOLD = 0.75

# ── Rate limiting ─────────────────────────────────────────────────────────────

# Seconds to wait between API search calls
# Increase if you hit rate limits; decrease to run faster
REQUEST_DELAY = 0.4

# ── Playlist limits ───────────────────────────────────────────────────────────

# Max playlists to fetch per service (increase if you have more than 50)
MAX_PLAYLISTS = 50

# ── Descriptions ─────────────────────────────────────────────────────────────

# Description added to playlists created by PlaysSync
SPOTIFY_PLAYLIST_DESC = "Synced from YouTube Music · github.com/YOUR_USERNAME/music-sync"
YTM_PLAYLIST_DESC     = "Synced from Spotify · github.com/YOUR_USERNAME/music-sync"
