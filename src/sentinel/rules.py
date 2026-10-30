"""Rules R1-R6 as pure functions: no I/O, no clock, no randomness, no LLM (invariant 1).

R1 (M1) and R2 (M2) exist so far; R3-R6 and structured egress follow in M2.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import destinations, effects, egress
from .destinations import domain_of
from .secret_scan import CREDENTIAL_ARG, SecretMatch
from .matcher import Match
from .models import EFFECT_PRECEDENCE, AgentAction, Capability, Effect, Evidence, ReasonCode, RuleId, TaskContract, ToolEntry


@dataclass(frozen=True)
class RuleResult:
    rule_id: RuleId
    effect: Effect
    reason_code: ReasonCode
    summary: str
    evidence: list[Evidence] = field(default_factory=list)
    agent_summary: str | None = None  # what the agent is told, if not the officer's summary (plan Q3: never coach it)


def rule_r1(action: AgentAction, contract: TaskContract, entry: ToolEntry) -> RuleResult | None:
    """R1: the action must be inside the permission slip, and its tool must be in the registry."""
    if not entry.known:
        return RuleResult(
            RuleId.R1, Effect.BLOCK, ReasonCode.NOT_IN_REGISTRY,
            f"Blocked: '{action.tool}' is not a registered tool, so Sentinel will not run it. "
            "Unknown tools are treated as untrusted.",
            [Evidence(kind="registry", detail=f"tool '{action.tool}' is not in the tool registry")])
    if action.tool not in contract.allowed_tools:
        allowed = ", ".join(contract.allowed_tools) or "nothing"
        return RuleResult(
            RuleId.R1, Effect.BLOCK, ReasonCode.NOT_IN_SLIP,
            f"Blocked: '{action.tool}' is not part of this task's permission slip. "
            f"The slip for \"{contract.objective}\" allows: {allowed}.",
            [Evidence(kind="slip", detail=f"'{action.tool}' is not in allowed_tools",
                      source_ref=contract.contract_id)])
    return None


_KIND_NOUN = {"email": "e-mail address", "url": "web address", "path": "file path", "repo": "repository",
              "channel": "channel", "page": "page"}


def rule_r1_recipient(action: AgentAction, entry: ToolEntry, contract: TaskContract, recipients: list[str],
                      unparseable: list[str]) -> RuleResult | None:
    """R1 (destination part): every destination must be a real one inside the slip's allowed list (e-mail domains,
    URL hosts or sandbox paths, by the tool's `destination_kind`). This also stops a model that invents an address
    ("vendor email", vendor@example.com) or sends a malformed or ambiguous URL or path."""
    if not entry.outbound:
        return None
    allowed_list = sorted({d.lower() for d in contract.allowed_recipient_domains})
    noun = _KIND_NOUN.get(entry.destination_kind, "destination")
    only = "replies" if entry.destination_kind == "email" else "sending"
    if unparseable:
        return RuleResult(
            RuleId.R1, Effect.BLOCK, ReasonCode.NOT_IN_SLIP,
            f"Blocked: the destination is not a valid {noun}. This task's permission slip allows {only} "
            f"only to: {', '.join(allowed_list) or 'nobody'}.",
            [Evidence(kind="recipient", detail=f"no valid {noun} found in the destination field")])
    outside = sorted({domain_of(r) for r in recipients if not destinations.allowed(r, allowed_list)})
    if outside:
        return RuleResult(
            RuleId.R1, Effect.BLOCK, ReasonCode.NOT_IN_SLIP,
            f"Blocked: this task's permission slip allows {only} only to {', '.join(allowed_list) or 'nobody'}; "
            f"{', '.join(outside)} is outside it.",
            [Evidence(kind="recipient", detail=f"{d} is not an allowed destination") for d in outside])
    return None


def rule_r1_egress(action: AgentAction, entry: ToolEntry, contract: TaskContract) -> RuleResult | None:
    """R1 (egress part): a tool that may only send through a fixed template must match that template exactly.
    Extra or missing fields, wrong formats and a quotation id other than the slip's work item are all refused."""
    if entry.egress_template is None:
        return None
    template = egress.find_template(contract, entry.egress_template)
    errors = ["this slip defines no such template"] if template is None else egress.validate(
        template, action.args, contract)
    if not errors:
        return None
    return RuleResult(
        RuleId.R1, Effect.BLOCK, ReasonCode.EGRESS_TEMPLATE_INVALID,
        f"Blocked: this task only allows Sentinel's fixed acknowledgement ({'; '.join(errors)}). "
        f"Call {action.tool} with the quotation id only.",
        [Evidence(kind="egress", detail=e, source_ref=entry.egress_template) for e in errors])


def rule_r3(action: AgentAction, entry: ToolEntry, recipients: list[str], untrusted: dict[str, str] | set[str],
            trusted: frozenset[str], untrusted_actions: dict[str, str] | None = None) -> RuleResult | None:
    """R3: a destination that appears only in untrusted content (and not in the trusted vendor records) is
    refused, even inside an allowed domain. Value-level provenance, not general flow tracking."""
    if not entry.outbound:
        return None
    # Only e-mail addresses: for a URL host or a path, the officer's allow-list in the slip is the control (R1), and a
    # document naming the very host the officer allowed must not make it unusable.
    bad = [r for r in recipients if "@" in r and r in untrusted and r not in trusted]
    if not bad:
        return None
    return RuleResult(
        RuleId.R3, Effect.BLOCK, ReasonCode.DEST_FROM_UNTRUSTED,
        f"Blocked: the recipient {', '.join(bad)} appears only inside a document the agent read, not in the "
        "trusted vendor records or the officer's slip. Reply to the vendor's registered address.",
        [Evidence(kind="provenance", detail=f"{r} was found in untrusted content and in no trusted source",
                  # the tool whose result held it, so the console can draw an honest link; a plain set carries no source
                  source_ref=untrusted.get(r, "untrusted tool result") if isinstance(untrusted, dict)
                  else "untrusted tool result",
                  source_action_id=(untrusted_actions or {}).get(r)) for r in bad])


def rule_r4(action: AgentAction, entry: ToolEntry, approved: bool) -> RuleResult | None:
    """R4: actions the registry marks for human verification need the officer's approval of this exact call."""
    if not entry.requires_human_verification or approved:
        return None
    return RuleResult(
        RuleId.R4, Effect.ASK, ReasonCode.HUMAN_VERIFICATION,
        f"Approval needed: '{action.tool}' is an action the officer must confirm. "
        "It will run only if the officer approves this exact request.",
        [Evidence(kind="approval", detail=f"'{action.tool}' requires human verification", source_ref=action.tool)])


def rule_r7(action: AgentAction, entry: ToolEntry, tainted_by: dict[str, str], recipients: list[str],
            contract: TaskContract, trusted: frozenset[str], approved: bool) -> RuleResult | None:
    """R7: once the session has read untrusted content (a document, a web page, an e-mail), a consequential action needs
    the officer's approval of that exact call, UNLESS it goes only to a destination the officer named in the slip as
    internal, or to a vendor on file, or is Sentinel's own fixed template. Read-only actions never ask.

    This needs no knowledge of what the untrusted content says, which is the point: a compromised PDF nobody has seen
    can still steer the agent, but it cannot make a consequential action happen without a human saying yes."""
    if approved or not tainted_by or not entry.consequential:
        return None
    if entry.egress_template is not None:
        return None  # a fixed message to a vendor resolved by Sentinel: nothing the content wrote can be in it
    if recipients and all(r in trusted or destinations.allowed(r, contract.internal_destinations) for r in recipients):
        return None
    source = sorted(tainted_by)[0]
    return RuleResult(
        RuleId.R7, Effect.ASK, ReasonCode.TAINTED_ACTION,
        f"Approval needed: this session has read untrusted content (from {source}), so '{action.tool}' "
        "needs the officer to approve this exact request. It will run only if the officer says yes.",
        [Evidence(kind="taint", detail=f"untrusted content was read from {s} earlier in this session", source_ref=s)
         for s in sorted(tainted_by)])


_KIND_LABEL = {"number": "quantity", "code": "depot code", "date": "date", "email": "e-mail address",
               "digits": "long number (phone or account)", "id": "identifier", "text": "passage of text"}


def rule_r2(action: AgentAction, entry: ToolEntry, matches: list[Match]) -> RuleResult | None:
    """R2: restricted values this session has read must not appear in anything leaving the building.

    The agent-facing summary never repeats the values (the agent would simply re-send them in another
    form); the evidence, which goes to the console and the audit log, does."""
    if not entry.outbound or not matches:
        return None
    labels = sorted({_KIND_LABEL.get(m.kind, m.kind) for m in matches})
    sources = sorted({m.source_ref for m in matches})
    evidence = [Evidence(kind="fingerprint",
                         detail=f"{_KIND_LABEL.get(m.kind, m.kind)} from {m.source_ref} found in argument '{m.path or action.tool}'",
                         matched_tokens=[m.snippet], source_ref=m.source_ref, source_action_id=m.source_action)
                for m in matches]
    return RuleResult(
        RuleId.R2, Effect.BLOCK, ReasonCode.SECRET_EGRESS,
        f"Blocked: this {action.tool} would send {len(matches)} restricted value(s) "
        f"({', '.join(labels)}) read from {', '.join(sources)} outside the building. "
        "This task's permission slip does not allow restricted data to leave. "
        "Send an acknowledgement without that information.",
        evidence,
        agent_summary=f"Blocked: this {action.tool} would send restricted data from this task outside the building, which "
                      "its permission slip does not allow. Send it without that information.")


def rule_r8(action: AgentAction, entry: ToolEntry, contract: TaskContract, tainted_by: dict[str, str],
            restricted_reads: dict[str, str], recipients: list[str], approved: bool) -> RuleResult | None:
    """R8, the Rule of Two (plan Q3; Meta's Agents Rule of Two, Willison's lethal trifecta). When the slip asks for it
    (strict_flows), a session that has read restricted data AND untrusted content may send outside its internal
    destinations only with the officer's approval of that exact call, a vendor on file included. Value matching (R2)
    cannot see a paraphrase ("plenty of stock at the western depot"); this rule does not need to see it, because it reasons
    about what the session has read, not about what the message says."""
    if approved or not contract.strict_flows or not entry.outbound or entry.egress_template is not None:
        return None
    if not tainted_by or not restricted_reads:
        return None
    if recipients and all(destinations.allowed(r, contract.internal_destinations) for r in recipients):
        return None
    restricted, untrusted = sorted(restricted_reads)[0], sorted(tainted_by)[0]
    return RuleResult(
        RuleId.R8, Effect.ASK, ReasonCode.RULE_OF_TWO,
        f"Approval needed: this session has read restricted data (from {restricted}) and untrusted content (from "
        f"{untrusted}), so anything '{action.tool}' sends outside could carry that data in other words. It will run only "
        "if the officer approves this exact request.",
        [Evidence(kind="flow", detail=f"restricted data was read from {s} earlier in this session", source_ref=s)
         for s in sorted(restricted_reads)] +
        [Evidence(kind="taint", detail=f"untrusted content was read from {s} earlier in this session", source_ref=s)
         for s in sorted(tainted_by)])


def rule_secret(action: AgentAction, entry: ToolEntry, matches: list[SecretMatch]) -> RuleResult | None:
    """R2 for credentials, and R9. A secret found in any tool result (a key in a runbook, a token in a ticket) is never sent
    anywhere, internal destinations included (R2), and is never used: a discovered credential in a credential-like argument,
    or in any action that does not send, was not issued to this task (R9). Plan Q2; PocketOS, Supabase MCP, Antigravity."""
    if not matches:
        return None
    used = [m for m in matches if CREDENTIAL_ARG.search(m.path or "")] or ([] if entry.outbound else matches)
    evidence = [Evidence(kind="secret", detail=f"{m.label} found in {m.source_ref}, present in argument '{m.path or action.tool}'",
                         matched_tokens=[m.masked], source_ref=m.source_ref, source_action_id=m.source_action) for m in matches]
    if used:
        return RuleResult(
            RuleId.R9, Effect.BLOCK, ReasonCode.DISCOVERED_CREDENTIAL,
            f"Blocked: this {action.tool} would use a credential that was found in data. Only credentials issued to this "
            "task may be used; this one was not.", evidence,
            agent_summary=f"Blocked: this {action.tool} would use a credential that was not issued to this task.")
    return RuleResult(
        RuleId.R2, Effect.BLOCK, ReasonCode.SECRET_EGRESS,
        f"Blocked: this {action.tool} would send a credential that was found in data. Credentials never leave, "
        "not even to an internal destination. Send it without that value.", evidence,
        agent_summary=f"Blocked: this {action.tool} would send a credential found in data. Send it without that value.")


def rule_effects(action: AgentAction, entry: ToolEntry, contract: TaskContract, approved: bool) -> list[RuleResult]:
    """What the action does, read from its arguments (plan Q4; effects.py). A path is checked whichever tool carries it, a SQL
    statement is classified whichever tool runs it, a shell command is tokenised before anyone decides about it.
    - agent and IDE configuration is never written (R1): a new MCP server or hook there runs code (CurXecute, Kiro);
    - credential files are never read (R1): .env, .ssh, keys (Antigravity, s1ngularity);
    - a read tool asked to change data, or a statement that cannot be read safely, is refused (R1);
    - a command that contacts a web address outside the slip is refused (R1);
    - anything that cannot be undone (DROP, DELETE without WHERE, rm -r, a cloud delete) waits for the officer (R4)."""
    out: list[RuleResult] = []
    writes = entry.capability in (Capability.WRITE, Capability.SEND) or entry.outbound
    for name, value in effects.paths_in_args(action.args):
        cls = effects.path_class(value)
        if cls == "config" and writes:
            out.append(RuleResult(RuleId.R1, Effect.BLOCK, ReasonCode.PROTECTED_PATH,
                                  f"Blocked: '{value}' is agent or editor configuration. An agent never writes there: a new "
                                  "server or hook in that file would run code on this machine.",
                                  [Evidence(kind="effect", detail=f"argument '{name}' is a protected configuration path")]))
        elif cls == "secret":
            out.append(RuleResult(RuleId.R1, Effect.BLOCK, ReasonCode.PROTECTED_PATH,
                                  f"Blocked: '{value}' holds credentials. An agent never reads credential files; only "
                                  "credentials issued to the task may be used.",
                                  [Evidence(kind="effect", detail=f"argument '{name}' is a credential file")]))
    for name in ("sql", "query", "statement"):
        sql = action.args.get(name) if isinstance(action.args, dict) else None
        if not isinstance(sql, str):
            continue
        fx = effects.sql_effect(sql)
        if fx.kind == "unknown" or (fx.kind in ("write", "ddl") and entry.capability == Capability.READ):
            why = fx.note or f"a {fx.kind} statement sent to a tool that may only read"
            out.append(RuleResult(RuleId.R1, Effect.BLOCK, ReasonCode.WRONG_EFFECT,
                                  f"Blocked: {why}. '{action.tool}' may only read data for this task.",
                                  [Evidence(kind="effect", detail=f"SQL classified as {fx.kind}"
                                            + (f" on {', '.join(fx.tables)}" if fx.tables else ""))]))
        elif fx.destructive and not approved:
            out.append(RuleResult(RuleId.R4, Effect.ASK, ReasonCode.DESTRUCTIVE,
                                  f"Approval needed: {fx.note}. It runs only if the officer approves this exact statement.",
                                  [Evidence(kind="effect", detail=fx.note)]))
    command = action.args.get("command") if isinstance(action.args, dict) else None
    if isinstance(command, str):
        fx = effects.shell_effect(command)
        for p in fx.reads_secret:
            out.append(RuleResult(RuleId.R1, Effect.BLOCK, ReasonCode.PROTECTED_PATH,
                                  f"Blocked: the command reads {p}, which holds credentials. An agent never reads credential "
                                  "files or the environment's secrets.",
                                  [Evidence(kind="effect", detail=f"the command reads {p}")]))
        for p in fx.writes_config:
            out.append(RuleResult(RuleId.R1, Effect.BLOCK, ReasonCode.PROTECTED_PATH,
                                  f"Blocked: the command writes {p}, which is agent or editor configuration.",
                                  [Evidence(kind="effect", detail=f"the command writes {p}")]))
        allowed_list = sorted({d.lower() for d in contract.allowed_recipient_domains})
        keys, bad = destinations.keys_in(list(fx.urls), "url")
        outside = sorted({domain_of(k) for k in keys if not destinations.allowed(k, allowed_list)})
        if outside or bad:
            out.append(RuleResult(RuleId.R1, Effect.BLOCK, ReasonCode.NOT_IN_SLIP,
                                  f"Blocked: the command contacts {', '.join(outside) or 'an address it could not read'}, "
                                  f"outside this task's permission slip ({', '.join(allowed_list) or 'nowhere'}).",
                                  [Evidence(kind="effect", detail=f"the command contacts {u}") for u in fx.urls]))
        if fx.destructive and not approved:
            out.append(RuleResult(RuleId.R4, Effect.ASK, ReasonCode.DESTRUCTIVE,
                                  "Approval needed: this command deletes or overwrites something that cannot be undone. "
                                  "It runs only if the officer approves this exact command.",
                                  [Evidence(kind="effect", detail="destructive: " + " | ".join(fx.programs))]))
    return out


FREEZE_AFTER_BLOCKS = 3


def rule_r5(action: AgentAction, entry: ToolEntry, contract: TaskContract, messages_out: int) -> RuleResult | None:
    """R5: outgoing messages stay within the slip's send budget. `messages_out` counts messages already
    allowed (reserved) in this session; a blocked attempt does not use any of the budget."""
    if not entry.outbound or messages_out < contract.max_messages:
        return None
    n = contract.max_messages
    return RuleResult(
        RuleId.R5, Effect.BLOCK, ReasonCode.VOLUME_EXCEEDED,
        f"Blocked: this task's permission slip allows {n} outgoing message{'s' if n != 1 else ''} and "
        f"{'that limit' if n == 1 else 'the limit'} has already been used.",
        [Evidence(kind="budget", detail=f"{messages_out} of {n} outgoing messages already used",
                  source_ref=contract.contract_id)])


def rule_r6(blocks_including_this: int, threshold: int = FREEZE_AFTER_BLOCKS) -> RuleResult | None:
    """R6: the Nth policy block in one session freezes it (three unless the slip says otherwise: freeze_after, plan Q3).
    Evaluated only when another rule already blocked."""
    if blocks_including_this < threshold:
        return None
    return RuleResult(
        RuleId.R6, Effect.FREEZE, ReasonCode.BLOCK_THRESHOLD_FREEZE,
        f"Frozen: this session made {blocks_including_this} blocked attempts and has been quarantined. "
        "No further actions are possible until the officer confirms a new permission slip.",
        [Evidence(kind="counter", detail=f"{blocks_including_this} policy blocks in this session")])


def combine(results: list[RuleResult]) -> RuleResult | None:
    """Pick the strongest verdict by precedence FREEZE > BLOCK > ASK > ALLOW. None when nothing fired."""
    for effect in EFFECT_PRECEDENCE:
        for r in results:
            if r.effect == effect:
                return r
    return None
