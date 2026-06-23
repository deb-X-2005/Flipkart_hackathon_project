#!/usr/bin/env bash
# Public URL via Cloudflare Tunnel (no signup, free).
# Prereq: brew install cloudflare/cloudflare/cloudflared  (mac)
#         or download from github.com/cloudflare/cloudflared/releases
set -euo pipefail
PORT="${TUNNEL_PORT:-5173}"
echo "Starting Cloudflare Tunnel for http://localhost:$PORT"
echo "(URL will appear below — share it with judges)"
exec cloudflared tunnel --url "http://localhost:$PORT" --no-autoupdate
