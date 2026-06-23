import pytest
from src.security import pii, classify, auth


def test_pii_strip_phone():
    assert "[REDACTED:PHONE]" in pii.strip("call 9876543210")
    assert "[REDACTED:PHONE]" in pii.strip("call +91 98765 43210")


def test_pii_strip_vehicle():
    assert "[REDACTED:VEHICLE]" in pii.strip("KA01AB1234 broke down")


def test_pii_strip_aadhaar():
    assert "[REDACTED:AADHAAR]" in pii.strip("aadhaar 1234 5678 9012")


def test_pii_strip_email_pan():
    out = pii.strip("contact a@b.com or PAN ABCDE1234F")
    assert "[REDACTED:EMAIL]" in out and "[REDACTED:PAN]" in out


def test_pii_scan_counts_categories():
    hits = pii.scan("ph 9876543210 mail a@b.com vehicle KA01AB1234")
    assert hits == {"PHONE": 1, "VEHICLE": 1, "EMAIL": 1}


def test_pii_strip_handles_non_string():
    assert pii.strip(None) is None
    assert pii.strip(42) == 42


def test_classify_levels():
    assert classify.classify("event_cause") == "public"
    assert classify.classify("priority") == "internal"
    assert classify.classify("address") == "sensitive"
    assert classify.classify("unknown_field") == "internal"


def test_classify_project_strips_higher_levels():
    row = {"event_cause": "x", "priority": "High", "address": "MG Rd"}
    assert classify.project(row, "public") == {"event_cause": "x"}
    proj_int = classify.project(row, "internal")
    assert "address" not in proj_int and "priority" in proj_int
    assert classify.project(row, "sensitive") == row


def test_jwt_human_roundtrip():
    tok = auth.issue("alice", role="operator")
    claims = auth.verify(tok)
    assert claims["sub"] == "alice"
    assert claims["role"] == "operator"
    assert claims["aud"] == "api"


def test_jwt_mcp_token_roundtrip():
    tok = auth.issue_mcp_token("agent-1", scopes=["forecast", "plan"])
    claims = auth.verify_mcp_token(tok)
    assert claims["sub"] == "agent-1"
    assert claims["aud"] == "mcp"
    assert claims["scopes"] == ["forecast", "plan"]


def test_cross_audience_rejected():
    import jwt as _jwt
    human = auth.issue("alice", "operator")
    agent = auth.issue_mcp_token("bot", scopes=[])
    with pytest.raises(_jwt.InvalidAudienceError):
        auth.verify_mcp_token(human)
    with pytest.raises(_jwt.InvalidAudienceError):
        auth.verify(agent)


def test_verify_any_accepts_both_kinds():
    for tok in (auth.issue("a", "operator"), auth.issue_mcp_token("b", [])):
        c = auth.verify_any(tok)
        assert c["aud"] in ("api", "mcp")


def test_fernet_roundtrip(crypto_env):
    from src.security.crypto import encrypt, decrypt
    pt = "MG Road, Bengaluru 560001"
    ct = encrypt(pt)
    assert ct and ct != pt
    assert decrypt(ct) == pt


def test_fernet_rejects_tampered(crypto_env):
    from src.security.crypto import encrypt, decrypt
    ct = encrypt("secret")
    with pytest.raises(ValueError):
        decrypt(ct[:-2] + "XX")


def test_audit_log_roundtrip(isolated_audit):
    isolated_audit.log("test.action", actor="alice", outcome="ok", custom=42)
    entries = isolated_audit.tail(5)
    assert any(e["action"] == "test.action" and e["custom"] == 42 for e in entries)
