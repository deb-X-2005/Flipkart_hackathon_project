# Public URL via Cloudflare Tunnel (no signup, free).
# Prereq:
#   winget install cloudflare.cloudflared
#   (or download from https://github.com/cloudflare/cloudflared/releases)
#
# Run AFTER `docker compose up` (or local dev) is already serving on :5173
$ErrorActionPreference = "Stop"
$PORT = if ($env:TUNNEL_PORT) { $env:TUNNEL_PORT } else { "5173" }
Write-Host "Starting Cloudflare Tunnel for http://localhost:$PORT" -ForegroundColor Cyan
Write-Host "(URL will appear below — share that with judges)" -ForegroundColor Cyan
cloudflared tunnel --url "http://localhost:$PORT" --no-autoupdate
