#!/usr/bin/env bash
# Headless-Chrome screenshot capture for docs/. Works on macOS and Linux;
# override the binary with CHROME=/path/to/chrome.
set -euo pipefail

PORT="${APPSHELL_PORT:-8765}"
BASE="http://localhost:${PORT}"
OUT="docs/screenshots"
CHROME="${CHROME:-}"

if [ -z "$CHROME" ]; then
  for candidate in \
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    "$(command -v google-chrome || true)" \
    "$(command -v chromium || true)"; do
    if [ -n "$candidate" ] && [ -x "$candidate" ]; then CHROME="$candidate"; break; fi
  done
fi
if [ -z "$CHROME" ]; then
  echo "No Chrome/Chromium found. Set CHROME=/path/to/chrome" >&2
  exit 1
fi

mkdir -p "$OUT"

shoot() {
  local path="$1" file="$2"
  "$CHROME" --headless --disable-gpu --hide-scrollbars \
    --window-size=1600,1000 --virtual-time-budget=5000 \
    --screenshot="$OUT/$file" "$BASE$path" 2>/dev/null
  echo "captured $OUT/$file"
}

shoot "/"         "dashboard.png"
shoot "/items"    "items.png"
shoot "/profiles" "profiles.png"
shoot "/users"    "users.png"

# Profile detail needs a real id from the seeded data.
PROFILE_ID=$(curl -s "$BASE/api/profiles?limit=1" | python3 -c "import json,sys; e=json.load(sys.stdin)['entries']; print(e[0]['id'] if e else '')")
if [ -n "$PROFILE_ID" ]; then
  shoot "/profiles/$PROFILE_ID" "profile-detail.png"
else
  echo "no profiles seeded; skipping profile-detail.png" >&2
fi
