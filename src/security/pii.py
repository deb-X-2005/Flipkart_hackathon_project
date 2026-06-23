"""PII stripper for free-text fields. GDPR Art 5 (data minimization) + Art 25 (privacy by design).

Targets common Indian PII patterns:
  - Phone numbers (10-digit, +91, with separators)
  - Aadhaar (12-digit, optionally space-grouped)
  - Vehicle registration (e.g. KA01AB1234)
  - Email
  - PAN (e.g. ABCDE1234F)
"""
import re

PATTERNS = {
    "PHONE":   re.compile(r"(?:\+?91[-\s]?)?(?:\d{5}[-\s]?\d{5}|\d{10})\b"),
    "AADHAAR": re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b"),
    "VEHICLE": re.compile(r"\b[A-Z]{2}[-\s]?\d{1,2}[-\s]?[A-Z]{1,2}[-\s]?\d{1,4}\b"),
    "EMAIL":   re.compile(r"\b[\w._%+-]+@[\w.-]+\.[A-Za-z]{2,}\b"),
    "PAN":     re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
}


def strip(text: str, mask: str = "[REDACTED:{kind}]") -> str:
    if not isinstance(text, str) or not text:
        return text
    out = text
    for kind, pat in PATTERNS.items():
        out = pat.sub(mask.format(kind=kind), out)
    return out


def scan(text: str) -> dict[str, int]:
    """Count PII hits per category (for audit logging without leaking values)."""
    if not isinstance(text, str) or not text:
        return {}
    return {k: len(p.findall(text)) for k, p in PATTERNS.items() if p.search(text)}


def strip_series(values):
    """Apply strip() over an iterable (e.g. pandas Series). Returns a list."""
    return [strip(v) if isinstance(v, str) else v for v in values]
