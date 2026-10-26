"""Session token and contract tests (G-005 token rules, ARCHITECTURE 5a, invariants 7 and 9)."""

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sentinel.contracts import (
    AUDIENCE,
    ISSUER,
    SessionError,
    SessionStore,
    draft_contract,
    load_templates,
    mint_session_token,
    verify_session_token,
)
from sentinel.models import Column, Mode, SessionStatus

NOW = datetime(2026, 10, 27, 10, 0, tzinfo=timezone.utc)


@pytest.fixture()
def key():
    return Ed25519PrivateKey.generate()


@pytest.fixture()
def contract():
    templates = load_templates()
    c = draft_contract(templates, "quotation_processing", officer="Col. R. Menon", now=NOW)
    return c


def mint(contract, key, column=Column.SENTINEL, now=NOW, ttl=900):
    contract = contract.model_copy(update={"status": SessionStatus.ACTIVE})
    return mint_session_token(contract, column, key, now=now, ttl_seconds=ttl)


def test_roundtrip_binds_contract_hash_and_column(contract, key):
    token, session_id = mint(contract, key)
    claims = verify_session_token(token, key.public_key(), now=NOW + timedelta(seconds=10))
    assert claims.session_id == session_id
    assert claims.contract_hash == contract.compute_hash()
    assert claims.column == Column.SENTINEL


def test_contract_hash_changes_when_slip_is_widened(contract):
    widened = contract.model_copy(update={"allowed_tools": contract.allowed_tools + ["delete_all"]})
    assert widened.compute_hash() != contract.compute_hash()


def test_status_change_does_not_change_contract_hash(contract):
    assert contract.compute_hash() == contract.model_copy(update={"status": SessionStatus.ACTIVE}).compute_hash()


def test_expired_token_rejected(contract, key):
    token, _ = mint(contract, key, ttl=60)
    with pytest.raises(SessionError, match="expired"):
        verify_session_token(token, key.public_key(), now=NOW + timedelta(seconds=61))


def test_token_signed_by_another_key_rejected(contract, key):
    token, _ = mint(contract, key)
    with pytest.raises(SessionError):
        verify_session_token(token, Ed25519PrivateKey.generate().public_key(), now=NOW)


def test_tampered_payload_rejected(contract, key):
    token, _ = mint(contract, key)
    head, payload, sig = token.split(".")
    forged = payload[:-2] + ("AA" if payload[-2:] != "AA" else "BB")
    with pytest.raises(SessionError):
        verify_session_token(f"{head}.{forged}.{sig}", key.public_key(), now=NOW)


def test_alg_none_rejected(contract, key):
    now = int(NOW.timestamp())
    unsigned = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "exp": now + 600, "iat": now, "jti": "ses_x",
         "contract_id": "tc_x", "contract_hash": "h", "column": "sentinel"},
        key=None, algorithm="none")
    with pytest.raises(SessionError):
        verify_session_token(unsigned, key.public_key(), now=NOW)


def test_hmac_confusion_rejected(contract, key):
    """A token signed with HS256 using the public key bytes must not verify (algorithm confusion)."""
    from cryptography.hazmat.primitives import serialization

    pub = key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    now = int(NOW.timestamp())
    forged = jwt.encode(
        {"iss": ISSUER, "aud": AUDIENCE, "exp": now + 600, "iat": now, "jti": "ses_x",
         "contract_id": "tc_x", "contract_hash": "h", "column": "sentinel"},
        pub, algorithm="HS256")
    with pytest.raises(SessionError):
        verify_session_token(forged, key.public_key(), now=NOW)


def test_wrong_audience_and_issuer_rejected(contract, key):
    now = int(NOW.timestamp())
    base = {"exp": now + 600, "iat": now, "jti": "ses_x", "contract_id": "tc_x",
            "contract_hash": "h", "column": "sentinel"}
    for claims in ({**base, "iss": ISSUER, "aud": "someone-else"}, {**base, "iss": "evil", "aud": AUDIENCE}):
        token = jwt.encode(claims, key, algorithm="EdDSA")
        with pytest.raises(SessionError):
            verify_session_token(token, key.public_key(), now=NOW)


def test_missing_expiry_rejected(contract, key):
    token = jwt.encode({"iss": ISSUER, "aud": AUDIENCE, "jti": "s", "contract_id": "c",
                        "contract_hash": "h", "column": "sentinel"}, key, algorithm="EdDSA")
    with pytest.raises(SessionError):
        verify_session_token(token, key.public_key(), now=NOW)


def test_revoked_token_rejected_immediately(contract, key):
    token, session_id = mint(contract, key)
    with pytest.raises(SessionError, match="revoked"):
        verify_session_token(token, key.public_key(), now=NOW, revoked={session_id})


def test_store_freeze_blocks_reuse_and_new_session_needs_new_token(contract, key):
    store = SessionStore()
    token, session_id = mint(contract, key)
    claims = verify_session_token(token, key.public_key(), now=NOW)
    store.add(claims, contract.model_copy(update={"status": SessionStatus.ACTIVE}))
    assert store.is_usable(session_id)
    store.freeze(session_id)
    assert not store.is_usable(session_id)
    assert session_id in store.revoked
    with pytest.raises(SessionError, match="revoked"):
        verify_session_token(token, key.public_key(), now=NOW, revoked=store.revoked)


def test_unknown_template_rejected():
    with pytest.raises(KeyError):
        draft_contract(load_templates(), "no_such_template", officer="x", now=NOW)


def test_draft_defaults_and_mode(contract):
    assert contract.status == SessionStatus.PENDING
    assert contract.mode == Mode.FINGERPRINT
    assert contract.allowed_tools == ["read_quotation", "query_stock", "send_email"]
    assert contract.contract_hash == contract.compute_hash()
    assert contract.expires_at > contract.issued_at
