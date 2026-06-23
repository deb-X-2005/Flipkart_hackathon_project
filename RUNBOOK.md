# Operational Runbook

ISO 27001 A.12.1 (operational procedures) + A.16.1 (incident management).

## Daily checks

- Confirm scrapers ran: `tail -5 logs/audit-$(date -u +%F).jsonl | grep scrape`
- Confirm forecast jobs ran: same file, action `forecast.run`
- Disk usage: `du -sh data/ logs/`

## Weekly

- `pip-audit` — patch any critical/high in 7 days
- Backup `data/` (DB + FAISS + CSV) off-host
- Review `logs/audit-*.jsonl` for `outcome:"fail"` clusters

## Incident response

### Suspected credential compromise

1. Revoke: rotate `AUTH_SECRET` (any active tokens immediately invalid).
2. Rotate `CRYPTO_KEY` if data-at-rest exposure suspected:
   - Decrypt existing values with old key, re-encrypt with new (script: TBD).
3. Audit: `grep auth.issue logs/audit-*.jsonl` for the compromised subject; correlate timestamps with intrusion window.
4. Notify: DPO + affected users within **72 h** (GDPR Art 33).

### PII leak detected in logs or output

1. Stop the offending pipeline.
2. Quarantine the affected file (move out of `data/` to `quarantine/`).
3. Identify upstream source — usually a scraper or unstripped description column.
4. Run `pii.scan()` over the file to enumerate categories present.
5. Re-process through `pii.strip()`, overwrite original.
6. File internal incident report; if subjects can be identified, notify per Art 34.

### Model drift / unreasonable predictions

1. Check input distribution vs training distribution (run EDA on last 30 days).
2. If `event_cause` distribution shifted > 20 %, retrain.
3. If a single feature dominates importance unexpectedly, investigate data corruption.
4. Roll back to previous `models/closure_clf.cbm` from backup.

## Key rotation procedure

`AUTH_SECRET`:
1. Generate new: `python -c "import secrets; print(secrets.token_urlsafe(48))"`
2. Set `AUTH_SECRET_NEXT` alongside `AUTH_SECRET` for the rollover window.
3. Issue new tokens with new secret; verify legacy tokens with old secret until TTL expiry.
4. Remove old secret after max TTL elapsed.

`CRYPTO_KEY`:
1. `python -c "from src.security.crypto import generate_key; print(generate_key())"`
2. Re-encrypt all rows in batches; coordinate downtime if needed.

## Disaster recovery

| Component | RPO | RTO | Restore from |
|---|---|---|---|
| Astram raw + processed CSVs | 24 h | 1 h | Daily backup of `data/` |
| FAISS index | 24 h | 15 min | Rebuild via `scripts/stage9_build_rag.py` |
| Audit logs | 0 | n/a | Append-only; never restore-overwrite |
| Model artifact | 24 h | 5 min | Re-train via `scripts/stage4_model.py` |

## Contacts

| Role | Person | Channel |
|---|---|---|
| Project lead | TBD | — |
| DPO         | TBD | — |
| On-call     | TBD | — |
