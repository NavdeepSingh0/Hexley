#!/usr/bin/env bash
# Give the server Google sign-in (D-060). Run it yourself, in your own terminal: it asks for the client secret without showing it, so it is
# never in a chat or in your shell history. The values stay in a file only root can read.
#   sudo bash set_google.sh "you@gmail.com,teammate@gmail.com"     (or "*" for any Google account)
set -euo pipefail

EMAILS="${1:?usage: set_google.sh <comma-separated addresses, or *>}"
ENV=/etc/hexley/hexley.env

read -r -p "Google client ID: " ID
read -rs -p "Google client secret (hidden): " SECRET
echo
[ -n "$ID" ] && [ -n "$SECRET" ] || { echo "Both are needed; nothing was changed." >&2; exit 1; }

sed -i -e '/^HEXLEY_GOOGLE_CLIENT_ID=/d' -e '/^HEXLEY_GOOGLE_CLIENT_SECRET=/d' -e '/^HEXLEY_OFFICER_EMAILS=/d' "$ENV"
umask 077
{
  echo "HEXLEY_GOOGLE_CLIENT_ID=$ID"
  echo "HEXLEY_GOOGLE_CLIENT_SECRET=$SECRET"
  echo "HEXLEY_OFFICER_EMAILS=$EMAILS"
} >> "$ENV"
echo "Saved. Who may sign in: $EMAILS"
