#!/usr/bin/env bash
# Sets up Hexley on a fresh Ubuntu server (D-055): Docker, 1 GB of swap, the image, and Caddy for HTTPS on the domain.
# Run once as a user with sudo, after loading the image with `docker load`. Safe to run again.
#   sudo bash ec2_setup.sh hexley.site
# The officer token is generated here and stays on the server, in a file only root can read. It is never printed.
set -euo pipefail

DOMAIN="${1:?usage: ec2_setup.sh <domain>}"
IMAGE="${IMAGE:-hexley-sentinel-test}"
CONF=/etc/hexley

if ! command -v docker >/dev/null; then
  apt-get update -y
  apt-get install -y docker.io
  systemctl enable --now docker
fi

if [ ! -f /swapfile ]; then
  fallocate -l 1G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

mkdir -p "$CONF"
chmod 700 "$CONF"
if [ ! -f "$CONF/hexley.env" ]; then
  umask 077
  {
    echo "SENTINEL_API_TOKEN=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
    echo "SENTINEL_PUBLIC_URL=https://$DOMAIN"
    echo "SENTINEL_OAUTH_PRESET=claude_connectors"
    echo "SENTINEL_OAUTH_DESTINATIONS="
    echo "SENTINEL_OAUTH_INTERNAL="
  } > "$CONF/hexley.env"
  echo "Wrote $CONF/hexley.env. Set the slip's destinations there, then run this again."
fi
# Compression and browser caching for the website only: the gateway and the API stream, and must not be buffered.
cat > "$CONF/Caddyfile" <<EOF
$DOMAIN {
  @pages not path /mcp* /api/* /events*
  encode @pages zstd gzip
  header /assets/* Cache-Control "public, max-age=2592000, immutable"
  header /console/assets/* Cache-Control "public, max-age=2592000, immutable"
  header /img/* Cache-Control "public, max-age=86400"
  reverse_proxy 127.0.0.1:10000
}
EOF

docker rm -f hexley >/dev/null 2>&1 || true
docker run -d --name hexley --restart always --env-file "$CONF/hexley.env" -e PORT=10000 \
  -p 127.0.0.1:10000:10000 "$IMAGE" >/dev/null

docker rm -f caddy >/dev/null 2>&1 || true
docker run -d --name caddy --restart always --network host -v caddy_data:/data \
  -v "$CONF/Caddyfile:/etc/caddy/Caddyfile:ro" caddy:2 >/dev/null

echo "Started. Checking the service (it can take a minute or two to answer):"
for _ in $(seq 1 60); do
  if curl -fsS http://127.0.0.1:10000/health >/dev/null 2>&1; then
    echo "Hexley answers on this server. Check https://$DOMAIN/health once the DNS record is in place."
    exit 0
  fi
  sleep 5
done
echo "Hexley did not answer in 5 minutes. See: sudo docker logs --tail 40 hexley" >&2
exit 1
