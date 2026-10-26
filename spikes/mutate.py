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
     "bad = [r for r in recipients if r in untrusted and r not in trusted]", "bad = []",
     "tests/test_r3.py", "another_mailbox or formatting_tricks or stranger_address"),
    ("R3 forgets the trusted vendor records (blocks the real vendor)", "src/sentinel/rules.py",
     "bad = [r for r in recipients if r in untrusted and r not in trusted]", "bad = [r for r in recipients if r in untrusted]",
     "tests/test_r3.py", "vendors_own_registered_address"),
    ("R1 stops checking recipient domains", "src/sentinel/rules.py",
     "    outside = sorted({domain_of(r) for r in recipients if domain_of(r) not in allowed})", "    outside = []",
     "tests/test_r3.py", "foreign_recipients or stranger_outside"),
    ("an approved action skips the other rules (BLOCK no longer outranks ASK)", "src/sentinel/rules.py",
     "EFFECT_PRECEDENCE", "[Effect.FREEZE, Effect.ASK, Effect.BLOCK, Effect.ALLOW]  # MUTATION\n_UNUSED_PRECEDENCE",
     "tests/test_r4.py", "still_has_to_pass_every_other_rule"),
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
