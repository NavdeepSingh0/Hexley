#!/usr/bin/env bash
# Gives the hosted chat one real connector (D-063). Run it on the server yourself; the token is typed here and never travels through a chat.
# Use a fine-grained GitHub token limited to your test repositories: Issues read and write, Contents read.
#
#   scp -i ~/.ssh/hexley.pem scripts/deploy/set_connector.sh ubuntu@<address>:/tmp/
#   ssh -t -i ~/.ssh/hexley.pem ubuntu@<address> "sudo bash /tmp/set_connector.sh"
set -euo pipefail

CONF=/etc/hexley/hexley.env
[ -w "$CONF" ] || { echo "Run this with sudo on the server."; exit 1; }

read -rs -p "GitHub token (hidden): " TOKEN </dev/tty; echo
read -r -p "Repositories it may write to, as owner/name, comma separated: " REPOS </dev/tty
[ -n "$TOKEN" ] && [ -n "$REPOS" ] || { echo "Both are needed. Nothing was changed."; exit 1; }

LIST=$(echo "$REPOS" | tr ',' '\n' | sed 's/^ *//; s/ *$//; /^$/d; s/^/repo:/' | paste -sd, -)
sed -i '/^GITHUB_TOKEN=/d; /^SENTINEL_CHAT_REPOS=/d' "$CONF"
printf 'GITHUB_TOKEN=%s\nSENTINEL_CHAT_REPOS=%s\n' "$TOKEN" "$LIST" >> "$CONF"
chmod 600 "$CONF"

# The container reads that file only when it is created. This keeps the same image.
IMAGE=$(docker inspect -f '{{.Config.Image}}' hexley)
docker rm -f hexley >/dev/null
docker run -d --name hexley --restart always --env-file "$CONF" -e PORT=10000 -p 127.0.0.1:10000:10000 "$IMAGE" >/dev/null
echo "Done. Hexley is restarting: everyone is signed out, and it answers again in about a minute."
