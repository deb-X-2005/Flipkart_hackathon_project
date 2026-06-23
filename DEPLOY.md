# Deploy / Public URL

Three paths, in order of friction. Pick whichever matches your submission window.

---

## Path A — Instant tunnel (60 seconds, free, requires your laptop on)

Gets you a `https://*.trycloudflare.com` URL that works in any browser. No signup.

**Install cloudflared (one-time):**

Windows:
```powershell
winget install cloudflare.cloudflared
```

Mac:
```bash
brew install cloudflare/cloudflare/cloudflared
```

Linux: download from https://github.com/cloudflare/cloudflared/releases

**Run (with the app already up locally):**

```powershell
# Windows
.\scripts\tunnel.ps1
```
```bash
# Mac / Linux
./scripts/tunnel.sh
```

Cloudflared prints a public URL like `https://random-words.trycloudflare.com` — that's what goes in your submission.

**Caveat:** judges can only reach it while your laptop is on with the tunnel + backend + frontend running.

---

## Path B — Render free tier (15 minutes, free, always-on URL)

Permanent URL like `https://event-traffic-frontend.onrender.com`. Sleeps after 15 min of inactivity, ~30 s cold start on first hit.

1. Push the repo to GitHub.
2. Sign up at https://render.com (free, GitHub login).
3. Dashboard → **New** → **Blueprint** → select your repo.
4. Render detects `render.yaml`. Click **Apply**.
5. In each service's env tab fill in the `sync: false` blanks:
   - **backend:** `CRYPTO_KEY` (generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`), `OPENROUTER_API_KEY` (sign up at openrouter.ai, $1 free credit), and after frontend deploys add its URL to `CORS_ORIGINS`.
   - **frontend:** `VITE_API_URL=https://event-traffic-backend.onrender.com`
6. Trigger a re-deploy on both. Submission URL is the frontend's URL.

**Why Ollama isn't used here:** Render free instances don't have the RAM/disk for it. Backend defaults to OpenRouter; switch to OpenAI/Anthropic in the LLM settings modal once signed in.

---

## Path C — Fly.io (10 minutes, free credit, always-on, faster cold start)

```bash
flyctl launch --copy-config --no-deploy   # creates fly.toml from Dockerfile
flyctl secrets set AUTH_SECRET="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
flyctl secrets set CRYPTO_KEY="$(python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')"
flyctl secrets set LLM_MODE=openrouter OPENROUTER_API_KEY=...
flyctl deploy
```

Frontend can ride on Vercel:
```bash
cd frontend && npx vercel --prod
# set VITE_API_URL=https://<your-fly-app>.fly.dev in Vercel env
```

---

## Local-only demo (no public URL)

If you'll demo on your own laptop with judges in the room, skip all of the above — `docker compose up` (or just the two dev servers) is enough.

---

## Which to pick?

| Scenario | Pick |
|---|---|
| Judging in <2 hours, your laptop will be on | **A** (cloudflared) |
| Judging spans days, permanent URL needed | **B** (Render) |
| Already on Fly.io / want faster cold starts | **C** |
| In-person demo only | local |
