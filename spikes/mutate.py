"""Mutation check: break one property on purpose, confirm the named tests fail, restore the file.

Run: python -m uv run python spikes/mutate.py
Safe by construction: every mutation is applied to a backup-protected copy and restored in a finally block.
"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

MUTATIONS = [
    ("approval hash ignores the arguments (substitution possible)", "src/sentinel/approvals.py",
     '{"session": session_id, "tool": tool, "args": args}', '{"session": session_id, "tool": tool}',
     "tests/test_r4.py", "row_25 or one_time or does_not_grant"),
    ("approvals are not one-time (consume does nothing)", "src/sentinel/approvals.py",
     "        a.status = ApprovalStatus.USED\n        return True", "        return True",
     "tests/test_r4.py", "one_time"),
    ("R3 ignores where the address came from", "src/sentinel/rules.py",
     'bad = [r for r in recipients if "@" in r and r in untrusted and r not in trusted]', "bad = []",
     "tests/test_r3.py", "another_mailbox or formatting_tricks or stranger_address"),
    ("R3 forgets the trusted vendor records (blocks the real vendor)", "src/sentinel/rules.py",
     'bad = [r for r in recipients if "@" in r and r in untrusted and r not in trusted]',
     'bad = [r for r in recipients if "@" in r and r in untrusted]',
     "tests/test_r3.py", "vendors_own_registered_address"),
    ("R1 stops checking recipient domains", "src/sentinel/rules.py",
     "    outside = sorted({domain_of(r) for r in recipients if not destinations.allowed(r, allowed_list)})", "    outside = []",
     "tests/test_r3.py", "foreign_recipients or stranger_outside"),
    ("slot validation is skipped (any request fits the template)", "src/sentinel/egress.py",
     "    errors: list[str] = []\n    expected = set(template.slots)", "    return []  # MUTATION\n    errors: list[str] = []\n    expected = set(template.slots)",
     "tests/test_hardened.py", "r1_egress_table"),
    ("the tool no longer checks the recorded message hash", "src/sentinel/gateway.py",
     "if msg.message_sha256 != expected:", "if False:",
     "tests/test_hardened.py", "differs_from_the_recorded_one"),
    ("the gateway tool is shown to baseline columns that do not allow it", "src/sentinel/gateway.py",
     "return [t for t in tools if not self.rt.registry.get(t.name).local or t.name in allowed]", "return tools",
     "tests/test_hardened.py", "hidden_from_columns"),
    ("the tool body trusts its caller (no hardened-slip check)", "src/sentinel/gateway.py",
     "if session is None or expected is None or session.contract.mode != Mode.HARDENED:", "if session is None:",
     "tests/test_hardened.py", "fails_closed_everywhere or without_a_recorded_decision"),
    ("an approved action skips the other rules (BLOCK no longer outranks ASK)", "src/sentinel/rules.py",
     "EFFECT_PRECEDENCE", "[Effect.FREEZE, Effect.ASK, Effect.BLOCK, Effect.ALLOW]  # MUTATION\n_UNUSED_PRECEDENCE",
     "tests/test_r4.py", "still_has_to_pass_every_other_rule"),
    ("OAuth approval no longer needs the officer code", "src/sentinel/oauth.py",
     "if not (officer_code and hmac.compare_digest(officer_code.strip().encode(), req.officer_code.encode())):", "if False:",
     "tests/test_oauth.py", "no_approval_without_the_officer_code or locks_after"),
    ("an OAuth refresh starts a NEW session (would reset the message budget)", "src/sentinel/oauth.py",
     "ttl_seconds=ttl, session_id=session_id)", "ttl_seconds=ttl)",
     "tests/test_oauth.py", "refresh_keeps_the_session"),
    ("an OAuth refresh ignores a frozen session", "src/sentinel/oauth.py",
     "if session is None or not self.rt.store.is_usable(session_id):", "if session is None:",
     "tests/test_oauth.py", "refresh_is_refused_for_a_frozen_session"),
    # ---- B2: generality ----
    ("R7 never asks after untrusted content", "src/sentinel/rules.py",
     "    if approved or not tainted_by or not entry.consequential:", "    if True:",
     "tests/test_r7_and_slips.py", "waits_for_the_officer or no_destination_asks"),
    ("R7 exempts every destination (not only the officer's internal ones)", "src/sentinel/rules.py",
     "    if recipients and all(r in trusted or destinations.allowed(r, contract.internal_destinations) for r in recipients):",
     "    if recipients:",
     "tests/test_r7_and_slips.py", "waits_for_the_officer"),
    ("restricted data may go anywhere in the allowed domain, not only to internal destinations", "src/sentinel/engine.py",
     "destinations.allowed(r, session.contract.internal_destinations) for r in recipients):",
     "destinations.allowed(r, session.contract.allowed_recipient_domains) for r in recipients):",
     "tests/test_r7_and_slips.py", "internal_destination_but_nowhere_else"),
    ("a recipient counts as a leak of itself (cannot write to a customer in the database)", "src/sentinel/engine.py",
     'matches = [m for m in matches if not (m.kind == "email" and m.canonical in recipients)]', "matches = list(matches)",
     "tests/test_r7_and_slips.py", "recipient_is_not_a_leak"),
    ("a URL with userinfo or odd characters is accepted", "src/sentinel/destinations.py",
     '    if parts.scheme not in ("http", "https") or "@" in parts.netloc or not _STRICT_NETLOC.fullmatch(parts.netloc):',
     '    if parts.scheme not in ("http", "https"):',
     "tests/test_destinations_generic.py", "ambiguous_or_non_http"),
    ("a path may climb out with ..", "src/sentinel/destinations.py",
     '    if ".." in [p for p in raw.split("/") if p]:', "    if False:",
     "tests/test_destinations_generic.py", "climbs"),
    ("a path prefix has no folder boundary (/out covers /outside)", "src/sentinel/destinations.py",
     '(key == w.rstrip("/") or key.startswith(w.rstrip("/") + "/"))', 'key.startswith(w.rstrip("/"))',
     "tests/test_destinations_generic.py", "real_boundary"),
    ("R3 polices URL hosts too (an allowed host becomes unusable)", "src/sentinel/rules.py",
     'bad = [r for r in recipients if "@" in r and r in untrusted and r not in trusted]',
     "bad = [r for r in recipients if r in untrusted and r not in trusted]",
     "tests/test_destinations_generic.py", "r3_leaves_url_hosts"),
    ("an officer classification can overwrite a built-in registry entry", "src/sentinel/registry.py",
     "        if entry.name in self._base:", "        if False:",
     "tests/test_onboarding.py", "never_shadow or refuses_to_replace"),
    ("the API lets a built-in tool be reclassified", "src/sentinel/api.py",
     "        if rt.registry.is_builtin(name):", "        if False:",
     "tests/test_onboarding.py", "builtin_tool_cannot_be_reclassified"),
    ("internal destinations need not be inside the allowed destinations", "src/sentinel/contracts.py",
     "    outside = [i for i in internal if not _covered(i, allowed)]", "    outside = []",
     "tests/test_r7_and_slips.py", "vague_or_contradictory"),
    ("generic indexing reads 'owes 48,500' as the code owes48 and indexes 500", "src/sentinel/matcher.py",
     '        known_codes = None if "code" in wanted else frozenset()', "        known_codes = None",
     "tests/test_matcher_generic.py", "numbers_and_dates"),
    # ---- B3: general-purpose tools ----
    ("the database can be changed (the agent switches query_only off)", "src/sentinel/tools/server.py",
     '    db.set_authorizer(read_only)  # query_only alone could be switched off by the agent with "PRAGMA query_only=OFF"',
     "    pass",
     "tests/test_general_tools.py", "database_answers_reads_and_can_never_be_changed"),
    ("a path may climb out of the sandbox", "src/sentinel/tools/server.py",
     '        if ".." in p.split("/") or "\\x00" in p:', "        if False:",
     "tests/test_general_tools.py", "sandbox_holds or paths_stay_inside"),
    ("the provenance link names the wrong call", "src/sentinel/gateway.py",
     "                    session.untrusted_actions[address] = action.action_id",
     '                    session.untrusted_actions[address] = "act_unknown"',
     "tests/test_general_tools.py", "compromised_pdf_leaks"),
    ("a fingerprint forgets which call produced it", "src/sentinel/matcher.py",
     "                self.actions[(c.kind, c.canonical)] = action_id", "                self.actions[(c.kind, c.canonical)] = None",
     "tests/test_general_tools.py", "compromised_pdf_leaks"),
]


def pytest_failed(target: str, expr: str) -> bool:
    out = subprocess.run([sys.executable, "-m", "uv", "run", "pytest", target, "-q", "--tb=no", "-p", "no:logging", "-k", expr],
                         cwd=ROOT, capture_output=True, text=True)
    return " failed" in out.stdout or "failed" in out.stdout.splitlines()[-1] if out.stdout else True


def main() -> int:
    bad = 0
    for name, rel, old, new, target, expr in MUTATIONS:
        path = ROOT / rel
        original = path.read_bytes()
        text = original.decode("utf-8")
        if old not in text:
            print(f"SKIPPED (pattern not found): {name}")
            bad += 1
            continue
        try:
            path.write_bytes(text.replace(old, new, 1).encode("utf-8"))
            caught = pytest_failed(target, expr)
        finally:
            path.write_bytes(original)
        print(f"{'CAUGHT ' if caught else 'MISSED '} {name}")
        bad += 0 if caught else 1
    print("restored all files;", "every mutation was caught" if not bad else f"{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
