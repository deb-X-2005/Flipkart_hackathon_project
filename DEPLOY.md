# Deploy — get a public URL

**Recommended:** Hugging Face Spaces (Docker) — free, 16 GB RAM, always-on, git-based, no credit card.

---

## Recommended: Hugging Face Spaces (15 min, free, always-on)

Result: a permanent URL like `https://<your-username>-event-traffic-forecasting.hf.space` you can paste in your submission.

### Prereqs
- GitHub repo with this code already pushed (Path B in section "Other options" if you haven't)
- A free Hugging Face account: https://huggingface.co/join
- An LLM key. **Recommended: OpenRouter** ($1 free credit on signup, plenty for the demo): https://openrouter.ai

### Steps

1. Go to https://huggingface.co/new-space
2. Fill in:
   - **Owner:** your username
   - **Space name:** `event-traffic-forecasting` (or anything)
   - **License:** MIT (or whatever you like)
   - **Space SDK:** **Docker** → select **Blank** template
   - **Hardware:** CPU basic (free)
   - **Public**
   - Click **Create Space**

3. The Space is now empty. Push our GitHub code to it as a second remote:
   ```powershell
   git remote add hf https://huggingface.co/spaces/<your-username>/event-traffic-forecasting
   git push hf main
   ```
   When prompted for password, paste an HF **access token** (https://huggingface.co/settings/tokens → New token, role=Write).

4. The Space starts building immediately. While it builds, set the secrets:
   In your Space → **Settings** → **Variables and secrets** → **New secret** for each:

   | Name | Value |
   |---|---|
   | `AUTH_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
   | `CRYPTO_KEY`  | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
   | `LLM_MODE`    | `openrouter` |
   | `OPENROUTER_API_KEY` | from openrouter.ai (starts with `sk-or-...`) |
   | `OPENROUTER_MODEL`   | `anthropic/claude-sonnet-4.5` (or `meta-llama/llama-3.3-70b-instruct` for cheaper) |

5. After secrets are set, click **Restart** on the Space.

6. Wait for build (~10 min the first time — installs torch, sentence-transformers, catboost). When status is green:
   - Click the Space URL at the top
   - Sign in as `admin / admin123` to test (these demo accounts are auto-seeded)
   - Run a query → first chat call hits OpenRouter, takes ~3-5 s

That URL is what goes in your hackathon submission.

### Updating after deploy
Every push to GitHub `main` won't auto-deploy to HF (separate remote). To redeploy:
```powershell
git push hf main
```

### Common pitfalls
- **Build fails on PyTorch / OOM** — HF free CPU has 16 GB which is fine. If it still OOMs, switch the embedding model to OpenAI embeddings (smaller footprint).
- **502 on /chat** — `OPENROUTER_API_KEY` wrong or balance $0. Click the LLM badge in the deployed app → **Test key** with your real key (admin role).
- **First request slow** — HF Spaces hibernate compute occasionally on free tier; cold start ~30 s. Subsequent requests are fast.

---

## Other options

### Cloudflare Tunnel — instant, free, but only while your laptop is on

```powershell
winget install cloudflare.cloudflared
.\scripts\tunnel.ps1
```

Prints a `https://*.trycloudflare.com` URL. Stays alive only while the tunnel + backend + frontend are running. Not suitable if judges hit it later — your machine has to be on.

### Render — free tier, 512 MB

```bash
# render.yaml is already in the repo, connect it via dashboard
```

Render's 512 MB is **tight** with this ML stack — sentence-transformers + PyTorch may OOM. If it works, you get a permanent URL. Free tier sleeps after 15 min idle.

### Railway — $5 free credit, 8 GB RAM

```bash
railway init
railway up
```

### Fly.io — $5 free credit, fast cold starts

```bash
flyctl launch --copy-config --no-deploy
flyctl secrets set AUTH_SECRET=... CRYPTO_KEY=... LLM_MODE=openrouter OPENROUTER_API_KEY=...
flyctl deploy
```

---

## What you get from any deploy

- ✅ Frontend + backend at one URL (same origin — the React build is served by FastAPI's static mount in the combined Docker image)
- ✅ All routes wired: `/auth/login`, `/auth/signup`, `/chat`, `/forecast`, `/realtime/*`, `/llm/*`
- ✅ Demo accounts auto-seeded: `viewer/viewer123`, `operator/operator123`, `admin/admin123`
- ❌ Ollama doesn't run on free hosts — use OpenRouter / OpenAI / Anthropic via the LLM Settings modal (admin role)
