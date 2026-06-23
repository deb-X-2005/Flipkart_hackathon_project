# Security & Compliance

This document maps the project's security controls to **ISO/IEC 27001:2022 Annex A** and **EU GDPR**.

## Scope

Software components: ingestion, preprocessing, ML model, RAG index, scrapers, planner, API, frontend. Hosting and physical controls are out of scope (deployment-dependent).

## Roles

| Role     | Permissions |
|----------|-------------|
| viewer   | Read public + internal fields; no PII; no plan execution |
| operator | Run forecasts, view all internal data, see PII when justified |
| admin    | All operator + erasure + key rotation |

Roles are encoded in JWT claims (`role`), verified per request — see `src/security/auth.py`.

## Control mapping (Annex A subset implemented)

| Control | Title | Implementation |
|---------|-------|----------------|
| A.5.1   | Information security policies | This document + DPIA.md + RUNBOOK.md |
| A.8.2   | Information classification    | `src/security/classify.py` — every event field tagged `public` / `internal` / `sensitive` |
| A.8.3   | Information handling          | `classify.project()` drops fields above caller's clearance |
| A.9.2   | User access management        | JWT-issued tokens with TTL; role-based deps in FastAPI |
| A.9.4   | Access to programs and source | Secrets only in `.env` (gitignored); `AUTH_SECRET`, `CRYPTO_KEY` validated at startup |
| A.10.1  | Cryptography                  | Fernet (AES-128-CBC + HMAC-SHA256) for sensitive fields at rest — `src/security/crypto.py` |
| A.12.3  | Backup                        | SQLite cache + CSV + FAISS files; back up `data/` daily (deployment-side) |
| A.12.4  | Logging & monitoring          | Structured JSON audit log per UTC day in `logs/audit-*.jsonl` — `src/security/audit.py` |
| A.13.1  | Network security              | TLS termination at reverse proxy in deployment; HTTP→HTTPS redirect |
| A.14.2.5| Secure development            | Input validation via Pydantic on API; type checks throughout |
| A.16.1  | Incident management           | See RUNBOOK.md |
| A.18.1.4| Privacy of PII                | Strip PII at ingest (`src/security/pii.py`); never log raw PII; right to erasure |

Controls not yet implemented in this MVP: A.6 (org of infosec), A.7 (HR), A.11 (physical), A.15 (suppliers), A.17 (business continuity). Document them when this leaves dev.

## GDPR articles addressed

| Article | Requirement | Implementation |
|---------|-------------|----------------|
| Art 5(1)(c) | Data minimisation | PII stripper applied at ingest; classification registry caps field exposure |
| Art 5(1)(e) | Storage limitation | `retention.run()` purges audit > 365 days, scrape > 30 days |
| Art 17  | Right to erasure | `erasure.erase(event_id)` removes from CSV + FAISS + cache, writes audit |
| Art 25  | Privacy by design | PII stripped at scraper boundary, not after |
| Art 30  | Records of processing | Audit log captures actor, action, resource, outcome |
| Art 32  | Security of processing | Fernet at-rest, JWT in transit, classified access |
| Art 35  | DPIA | See DPIA.md |

## Secrets

Required env vars (all in `.env`, never committed):

```
AUTH_SECRET       # JWT signing key (>= 32 random bytes)
CRYPTO_KEY        # Fernet key, generate via crypto.generate_key()
DATAGOV_API_KEY   # optional, for data.gov.in
OPENAI_API_KEY    # optional, if LLM_MODE=openai
ANTHROPIC_API_KEY # optional, if LLM_MODE=anthropic
```

Rotate `AUTH_SECRET` and `CRYPTO_KEY` annually or on suspected compromise. Rotation procedure in RUNBOOK.md.

## Audit log format

One JSON line per event under `logs/audit-YYYY-MM-DD.jsonl`:

```json
{"ts":"2026-06-23T08:15:22.341Z","host":"...","pid":12345,
 "actor":"operator1","action":"forecast.run","resource":"event:abc",
 "outcome":"ok","closure_prob":0.82}
```

Retention: 365 days by default (`RETENTION_AUDIT_DAYS`). Logs are append-only; do not edit.

## Vulnerability tracking

Dependency vulnerabilities: run `pip-audit` weekly. Address criticals within 7 days, highs within 30.
