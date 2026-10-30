#!/usr/bin/env bash
# Give the server the hosted model's keys, for the live model in Hexley Chat. Run it yourself, in your own terminal: it asks without showing
# them, so they are never in a chat or in your shell history. They stay in a file only root can read.
#   sudo bash set_model_keys.sh
# Several keys let a rate limit on one move the chat to the next. SENTINEL_LIVE_MODEL_CAP limits the requests this deployment may send.
set -euo pipefail

ENV=/etc/hexley/hexley.env
keys=()
while true; do
  read -rs -p "NVIDIA API key $((${#keys[@]} + 1)) (hidden; just press Enter when you have no more): " KEY
  echo
  [ -z "$KEY" ] && break
  keys+=("$KEY")
done
[ "${#keys[@]}" -gt 0 ] || { echo "No key given; nothing was changed." >&2; exit 1; }

sed -i -e '/^NVIDIA_API_KEY/d' -e '/^SENTINEL_LIVE_MODEL_CAP=/d' "$ENV"
umask 077
{
  echo "SENTINEL_LIVE_MODEL_CAP=${LIVE_CAP:-300}"
  for i in "${!keys[@]}"; do
    if [ "$i" -eq 0 ]; then echo "NVIDIA_API_KEY=${keys[$i]}"; else echo "NVIDIA_API_KEY_$((i + 1))=${keys[$i]}"; fi
  done
} >> "$ENV"
echo "Saved ${#keys[@]} key(s). This deployment may send at most ${LIVE_CAP:-300} requests to the hosted model."
