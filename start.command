#!/bin/bash
# Start the Grace House Hymnal. Double-click me in Finder.
#
# This script:
#   1. Makes sure Tailscale is running (starts it if not)
#   2. Makes sure Funnel is exposing port 8000 (turns it on if not)
#   3. Starts the hymnal server
#
# In the normal case (everything already running from a previous session
# or from boot), it starts the server immediately with no prompts.
# If Tailscale or Funnel got stopped, it may ask for your Mac password
# to restart them.

cd "$(dirname "$0")"

# ── Find python3 ─────────────────────────────────────────────
PY=$(command -v python3)
if [ -z "$PY" ]; then
  echo "ERROR: python3 was not found."
  echo "macOS ships with Python 3. If missing:  xcode-select --install"
  echo
  read -n 1 -s -r -p "Press any key to close."
  exit 1
fi

# ── Find tailscale ───────────────────────────────────────────
TAILSCALE=""
for CANDIDATE in /opt/homebrew/bin/tailscale /usr/local/bin/tailscale; do
  if [ -x "$CANDIDATE" ]; then TAILSCALE="$CANDIDATE"; break; fi
done
if [ -z "$TAILSCALE" ] && command -v tailscale >/dev/null 2>&1; then
  TAILSCALE=$(command -v tailscale)
fi

# ── Find brew (for services) ─────────────────────────────────
BREW=""
for CANDIDATE in /opt/homebrew/bin/brew /usr/local/bin/brew; do
  if [ -x "$CANDIDATE" ]; then BREW="$CANDIDATE"; break; fi
done

# ── Check Tailscale daemon ───────────────────────────────────
TAILSCALE_UP=0
if [ -n "$TAILSCALE" ]; then
  if "$TAILSCALE" status --self=true >/dev/null 2>&1; then
    TAILSCALE_UP=1
  fi
fi

# ── Check Funnel status ──────────────────────────────────────
FUNNEL_UP=0
FUNNEL_URL=""
if [ $TAILSCALE_UP -eq 1 ]; then
  FUNNEL_OUT=$("$TAILSCALE" funnel status 2>&1)
  FUNNEL_URL=$(echo "$FUNNEL_OUT" | grep -oE 'https://[^ ]*ts\.net[^ ]*' | head -1)
  if [ -n "$FUNNEL_URL" ]; then
    FUNNEL_UP=1
  fi
fi

# ── If anything's off, offer to fix it ───────────────────────
if [ -z "$TAILSCALE" ]; then
  echo "──────────────────────────────────────────────────────────────"
  echo "  Tailscale isn't installed. See SETUP.md section 2-3."
  echo "  The hymnal will still start locally on this Mac, but"
  echo "  phones scanning the QR won't be able to reach it."
  echo "──────────────────────────────────────────────────────────────"
  echo
elif [ $TAILSCALE_UP -eq 0 ]; then
  echo "──────────────────────────────────────────────────────────────"
  echo "  Tailscale daemon isn't running. Starting it (may prompt for"
  echo "  your Mac password)..."
  echo "──────────────────────────────────────────────────────────────"
  if [ -n "$BREW" ]; then
    sudo "$BREW" services start tailscale 2>&1
    sleep 3
  else
    echo "  brew not found — start tailscale manually:"
    echo "      sudo brew services start tailscale"
  fi
  echo
  # Re-check funnel now that daemon should be up
  FUNNEL_OUT=$("$TAILSCALE" funnel status 2>&1)
  FUNNEL_URL=$(echo "$FUNNEL_OUT" | grep -oE 'https://[^ ]*ts\.net[^ ]*' | head -1)
  if [ -n "$FUNNEL_URL" ]; then FUNNEL_UP=1; fi
fi

if [ -n "$TAILSCALE" ] && [ $FUNNEL_UP -eq 0 ] && [ $TAILSCALE_UP -eq 1 ]; then
  echo "──────────────────────────────────────────────────────────────"
  echo "  Funnel is off. Turning it on for port 8000 (may prompt for"
  echo "  your Mac password)..."
  echo "──────────────────────────────────────────────────────────────"
  sudo "$TAILSCALE" funnel --bg 8000 2>&1
  sleep 1
  FUNNEL_OUT=$("$TAILSCALE" funnel status 2>&1)
  FUNNEL_URL=$(echo "$FUNNEL_OUT" | grep -oE 'https://[^ ]*ts\.net[^ ]*' | head -1)
  echo
fi

# ── Show the URL if we've got it ─────────────────────────────
if [ -n "$FUNNEL_URL" ]; then
  KEY=$(head -1 access-key.txt 2>/dev/null | tr -d '[:space:]')
  if [ -n "$KEY" ]; then
    echo "  Live at:  ${FUNNEL_URL%/}/$KEY/"
    echo
  fi
fi

# ── Start the hymnal server ──────────────────────────────────
exec "$PY" server.py
