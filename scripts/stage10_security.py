"""Stage 10 demo: exercise every security module end-to-end."""
from pathlib import Path
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Set test keys for the demo (in production these come from .env / secrets manager)
os.environ.setdefault("AUTH_SECRET", "demo-secret-change-me")

from src.security import pii, audit, auth, classify, retention
from src.security.crypto import encrypt, decrypt, generate_key


def main() -> None:
    print("== PII strip ==")
    text = "Vehicle KA01AB1234 broke down. Call driver 9876543210 or +91 98765 43210, email driver@example.com. Aadhaar 1234 5678 9012, PAN ABCDE1234F"
    stripped = pii.strip(text)
    hits = pii.scan(text)
    print(f"  hits: {hits}")
    print(f"  stripped: {stripped}")

    print("\n== Data classification ==")
    sample = {"event_cause": "accident", "corridor": "Mysore Road", "address": "MG Road, BLR", "veh_no": "KA01AB1234", "severity_score": 0.7}
    for level in ("public", "internal", "sensitive"):
        kept = classify.project(sample, level)
        print(f"  level={level}: {list(kept)}")

    print("\n== Audit log ==")
    audit.log("forecast.run", actor="operator1", resource="event:abc", outcome="ok", closure_prob=0.82)
    audit.log("gdpr.dsar", actor="dpo@example.com", resource="subject:user42", outcome="ok")
    recent = audit.tail(2)
    print(f"  last 2 entries:")
    for r in recent:
        print(f"   {r['ts']}  {r['action']:20} actor={r['actor']:24} outcome={r['outcome']}")

    print("\n== Encryption (Fernet) ==")
    os.environ["CRYPTO_KEY"] = generate_key()  # ephemeral key for the demo
    ct = encrypt("MG Road, Bengaluru 560001")
    pt = decrypt(ct)
    print(f"  ciphertext len: {len(ct)}  prefix: {ct[:30]}...")
    print(f"  roundtrip ok: {pt == 'MG Road, Bengaluru 560001'}")

    print("\n== Auth tokens (JWT) ==")
    tok_admin = auth.issue("alice@gov.in", role="admin", ttl=60)
    tok_viewer = auth.issue("bob@gov.in", role="viewer", ttl=60)
    print(f"  admin token len: {len(tok_admin)}")
    print(f"  decoded admin: {auth.verify(tok_admin)}")
    print(f"  decoded viewer: {auth.verify(tok_viewer)}")

    print("\n== Retention sweep ==")
    out = retention.run()
    print(f"  purged: {out}")

    print("\n== ISO 27001 / GDPR control map ==")
    for ctl, where in [
        ("A.8.2 Data classification", "src/security/classify.py"),
        ("A.9 Access control / RBAC", "src/security/auth.py"),
        ("A.10.1 Cryptography at rest", "src/security/crypto.py"),
        ("A.12.4 Audit logging",       "src/security/audit.py"),
        ("A.18.1 PII protection",      "src/security/pii.py"),
        ("GDPR Art 17 erasure",        "src/security/erasure.py"),
        ("GDPR Art 5(1)(e) retention", "src/security/retention.py"),
    ]:
        print(f"  {ctl:35} -> {where}")


if __name__ == "__main__":
    main()
