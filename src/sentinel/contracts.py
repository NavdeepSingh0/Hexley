"""Permission slips (task contracts) and session tokens.

The officer confirms a slip in the console; Sentinel then mints an EdDSA token bound to the
contract hash. The agent only ever holds the token. See ARCHITECTURE.md section 5a.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import yaml
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from . import fixtures
from .matcher import FingerprintIndex
from .models import Column, EgressTemplate, Mode, SessionStatus, TaskContract

ISSUER = "sentinel"
AUDIENCE = "sentinel-gateway"
ALGORITHMS = ["EdDSA"]  # the only permitted algorithm
CLOCK_SKEW_SECONDS = 30
CONFIG_DIR = Path(__file__).parent / "config"


class SessionError(Exception):
    """A session token or session is not acceptable. Callers must fail closed."""


# ---- slip templates ----------------------------------------------------------------------------
def load_templates(path: Path | None = None) -> dict[str, dict]:
    path = path or CONFIG_DIR / "templates.yaml"
    templates = yaml.safe_load(path.read_text(encoding="utf-8"))
    for name, spec in templates.items():  # validate egress templates at startup
        for et in spec.get("egress_templates", []):
            EgressTemplate(**et)
        for required in ("objective", "allowed_tools", "resource_classes", "allowed_recipient_domains",
                         "max_records", "max_messages", "max_records_out", "ttl_seconds"):
            if required not in spec:
                raise ValueError(f"template {name!r} is missing {required!r}")
        Mode(spec.get("mode", "fingerprint"))  # an unknown mode stops startup
        if spec.get("mode") == "hardened" and not spec.get("egress_templates"):
            raise ValueError(f"hardened template {name!r} has no egress template")
        if spec.get("requires_work_item") and not spec.get("egress_templates"):
            raise ValueError(f"template {name!r} requires a work item but defines no egress template")
    return templates


class SlipError(ValueError):
    """The slip cannot be drafted as asked (mode mismatch, missing or unresolvable work item)."""


def draft_contract(templates: dict[str, dict], template: str, officer: str, now: datetime | None = None,
                   mode: Mode | None = None, work_item_id: str | None = None) -> TaskContract:
    """Build a pending slip from a template. KeyError for an unknown template, SlipError for anything else.

    The template sets the mode (an explicit `mode` that disagrees is refused). A work item is resolved
    through the trusted intake queue to a vendor in the vendor master (D-019); the document's own claims
    about who sent it are never consulted."""
    spec = templates[template]
    template_mode = Mode(spec.get("mode", "fingerprint"))
    if mode is not None and mode != template_mode:
        raise SlipError(f"template {template!r} runs in {template_mode.value} mode, not {mode.value}")
    resolved_vendor = None
    if spec.get("requires_work_item") and not work_item_id:
        raise SlipError(f"template {template!r} needs a work item (a quotation id)")
    if work_item_id:
        vendor_key = fixtures.INTAKE.get(work_item_id)
        if vendor_key is None or vendor_key not in fixtures.VENDOR_MASTER:
            raise SlipError(f"work item {work_item_id!r} is not in the intake queue")
        vendor = fixtures.VENDOR_MASTER[vendor_key]
        domain = vendor["email"].rsplit("@", 1)[-1]
        if domain not in spec["allowed_recipient_domains"]:
            raise SlipError(f"the vendor's domain {domain!r} is not allowed by this slip")
        resolved_vendor = {"key": vendor_key, "name": vendor["name"], "email": vendor["email"]}
    now = now or datetime.now(timezone.utc)
    contract = TaskContract(
        contract_id=f"tc_{uuid.uuid4().hex[:12]}",
        template=template,
        objective=" ".join(str(spec["objective"]).split()),
        officer=officer,
        mode=template_mode,
        work_item_id=work_item_id,
        resolved_vendor=resolved_vendor,
        allowed_tools=list(spec["allowed_tools"]),
        resource_classes=list(spec["resource_classes"]),
        allowed_recipient_domains=list(spec["allowed_recipient_domains"]),
        max_records=spec["max_records"],
        max_messages=spec["max_messages"],
        max_records_out=spec["max_records_out"],
        egress_templates=[EgressTemplate(**et) for et in spec.get("egress_templates", [])],
        issued_at=now,
        expires_at=now + timedelta(seconds=spec["ttl_seconds"]),
        status=SessionStatus.PENDING,
    )
    return contract.model_copy(update={"contract_hash": contract.compute_hash()})


# ---- tokens ------------------------------------------------------------------------------------
@dataclass(frozen=True)
class SessionClaims:
    session_id: str
    contract_id: str
    contract_hash: str
    column: Column
    expires_at: datetime


def mint_session_token(contract: TaskContract, column: Column, key: Ed25519PrivateKey, *,
                       now: datetime | None = None, ttl_seconds: int = 900) -> tuple[str, str]:
    """Mint a token for an ACTIVE contract. Returns (token, session_id)."""
    if contract.status != SessionStatus.ACTIVE:
        raise SessionError("a token is minted only for a contract the officer has confirmed")
    now = now or datetime.now(timezone.utc)
    session_id = f"ses_{uuid.uuid4().hex[:12]}"
    payload = {
        "iss": ISSUER, "aud": AUDIENCE, "jti": session_id,
        "iat": int(now.timestamp()), "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
        "contract_id": contract.contract_id, "contract_hash": contract.compute_hash(),
        "column": column.value,
    }
    return jwt.encode(payload, key, algorithm="EdDSA"), session_id


def verify_session_token(token: str, public_key: Ed25519PublicKey, *, now: datetime | None = None,
                         revoked: set[str] | frozenset[str] = frozenset()) -> SessionClaims:
    """Check signature, algorithm, issuer, audience, expiry and revocation. Raises SessionError."""
    now = now or datetime.now(timezone.utc)
    try:
        # PyJWT's own clock checks are off: every time claim is compared with `now` below, so the
        # clock is injectable and the same code path runs in tests and in production.
        claims = jwt.decode(token, public_key, algorithms=ALGORITHMS, audience=AUDIENCE, issuer=ISSUER,
                            options={"require": ["exp", "iat", "jti", "iss", "aud"], "verify_exp": False,
                                     "verify_iat": False, "verify_nbf": False})
    except jwt.PyJWTError as e:
        raise SessionError(f"invalid session token: {type(e).__name__}") from e
    if int(claims["exp"]) <= int(now.timestamp()):
        raise SessionError("session token expired")
    if int(claims["iat"]) > int(now.timestamp()) + CLOCK_SKEW_SECONDS:
        raise SessionError("session token issued in the future")
    if claims["jti"] in revoked:
        raise SessionError("session revoked")
    try:
        return SessionClaims(
            session_id=claims["jti"], contract_id=claims["contract_id"],
            contract_hash=claims["contract_hash"], column=Column(claims["column"]),
            expires_at=datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc))
    except (KeyError, ValueError) as e:
        raise SessionError("session token is missing required claims") from e


# ---- session state -----------------------------------------------------------------------------
@dataclass
class Session:
    claims: SessionClaims
    contract: TaskContract
    status: SessionStatus = SessionStatus.ACTIVE
    blocks: int = 0
    messages_out: int = 0
    records_out: int = 0
    index: FingerprintIndex = field(default_factory=FingerprintIndex)  # restricted values read so far
    # addresses seen in untrusted tool results, each mapped to the tool whose result contained it first
    untrusted_destinations: dict[str, str] = field(default_factory=dict)
    trusted_addresses: frozenset[str] = frozenset()  # vendor-master addresses (trusted records), set at confirmation
    # Held across "decide + reserve budget + count the block", so concurrent calls cannot both take the last slot.
    lock: asyncio.Lock = field(default_factory=asyncio.Lock, repr=False)

    @property
    def session_id(self) -> str:
        return self.claims.session_id

    @property
    def column(self) -> Column:
        return self.claims.column


@dataclass
class SessionStore:
    sessions: dict[str, Session] = field(default_factory=dict)
    revoked: set[str] = field(default_factory=set)

    def add(self, claims: SessionClaims, contract: TaskContract) -> Session:
        # The stored contract must be exactly what the token was bound to.
        if contract.compute_hash() != claims.contract_hash:
            raise SessionError("contract does not match the token's contract hash")
        session = Session(claims=claims, contract=contract)
        self.sessions[claims.session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        return self.sessions.get(session_id)

    def is_usable(self, session_id: str) -> bool:
        s = self.sessions.get(session_id)
        return s is not None and s.status == SessionStatus.ACTIVE and session_id not in self.revoked

    def freeze(self, session_id: str) -> None:
        """Freeze and revoke immediately (R6 / kill switch). The token cannot be reused."""
        if session_id in self.sessions:
            self.sessions[session_id].status = SessionStatus.FROZEN
        self.revoked.add(session_id)
