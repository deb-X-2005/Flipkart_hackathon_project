# Data Protection Impact Assessment (DPIA)

GDPR Art 35. Reviewed and updated on each material change to data flows.

## 1. Processing description

The system ingests historical traffic-event records (Astram dataset, Bengaluru), real-time weather (Open-Meteo), news (GDELT, Google News RSS), and social signals (Reddit RSS) to predict event-driven congestion and propose mitigation plans (officers, barricades, diversions). Outputs are surfaced to traffic-police operators via a map UI and an API.

## 2. Lawful basis (Art 6)

| Data category | Basis |
|---|---|
| Astram event records (incl. addresses, vehicle nos.) | Public interest in road safety + contractual data sharing with traffic police |
| Weather data | Open data, no personal data |
| GDELT / News RSS | Publicly available; journalistic exemption |
| Reddit RSS | Publicly posted content; no profiling of individuals |

No special-category data (Art 9) is processed.

## 3. Categories of personal data

| Field | Category | Retention |
|---|---|---|
| Vehicle registration (`veh_no`) | Indirect identifier | Stripped at ingest |
| Address (`address`, `end_address`) | Location data | Encrypted at rest |
| Officer / police IDs (`assigned_to_police_id`, `kgid`, etc.) | Employee identifier | Encrypted at rest, internal-only |
| Free-text descriptions | May contain phones/Aadhaar/PAN | Regex-stripped at ingest |
| Scraped social posts | Publicly posted | 30-day TTL |

## 4. Risks identified

| # | Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|---|
| 1 | PII leak via free-text description | Medium | High | `pii.strip()` applied before storage; `pii.scan()` audits any unfiltered residual |
| 2 | Re-identification via vehicle no. + timestamp | Low | Medium | Vehicle no. stripped; address encrypted |
| 3 | Audit log itself contains PII | Low | High | Audit logger receives only structured fields, never raw text |
| 4 | Scraped Reddit/News posts about identifiable persons | Medium | Low | 30-day retention; no profile-building over time |
| 5 | Model trained on PII-bearing features | Low | Medium | Feature set excludes PII columns (see `classify.py` registry) |
| 6 | Forecasts wrongly used to target individuals | Low | High | Operator-only access; audit log on every forecast |

## 5. Data subject rights (Arts 12–22)

| Right | Where implemented |
|---|---|
| Access (Art 15) | DSAR endpoint (Stage 13: `GET /dsar?subject=`) — operator-role required |
| Rectification (Art 16) | Operator can correct records via API; audit logged |
| Erasure (Art 17) | `erasure.erase(event_id)` — admin only |
| Portability (Art 20) | CSV export endpoint (Stage 13) |
| Object (Art 21) | Manual review; opt-out persisted in `data/optouts.txt` |

## 6. Cross-border transfers

None in MVP. If the LLM mode is `openai` or `anthropic`, prompts may include redacted event descriptions; these providers operate under SCCs/Adequacy frameworks. Default `LLM_MODE=local` avoids transfers entirely.

## 7. DPO / contact

Designated DPO: TBD before production. Until then, escalate to project lead.

## 8. Review

Quarterly, or on any change to data sources / model features / LLM backend.
