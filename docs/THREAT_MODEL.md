# Threat model: what Sentinel guarantees, and what it does not

One page, written for judges' questions and for anyone connecting a real agent. It states what is protected, who is trusted, what happens when something is unclear, and which routes are outside the guarantee. Each claim names the evidence; nothing here is a claim of general security. See [README.md](../README.md) for measured results and [DECISIONS.md](DECISIONS.md) for the reasoning.

## 1. What "safe" means here

Sentinel does not define an action as safe because it matches the task. An action is allowed only when **all four** hold:

1. **Operation:** the tool is in the officer's permission slip and in the tool registry (R1).
2. **Target:** the destination is inside what the slip allows, and was not taken only from untrusted content (R1, R3).
3. **Data flow:** no restricted value the session has read is in anything leaving the building, unless the slip names the destination as internal (R2).
4. **Circumstance:** after the session has read untrusted content, a consequential action goes only to an internal destination, the vendor on file or Sentinel's fixed template, or else the officer approves that exact call (R7, R4).

What Sentinel does **not** check: whether the *content* of an allowed action is correct or wise (see section 5, integrity).

## 2. Who and what is trusted (the trusted computing base)

| Assertion | Authority | If it is wrong |
|---|---|---|
| Who the officer is | One static API token, and a one-time officer code for OAuth approval. **Demo-grade, not identity management** | Anyone holding the token can confirm a slip |
| What the task may do | The slip, confirmed by the officer before the agent reads anything untrusted. The agent cannot create or widen a slip | A too-wide slip is enforced faithfully |
| What a tool is (reads or sends, trusted or untrusted output, restricted data) | `config/registry.yaml`, plus an officer-made overlay. An unclassified tool is invisible and blocked | **A tool the officer classifies wrongly is trusted as classified.** Fail-closed covers unknown tools, not misclassified ones |
| Which vendor a quotation belongs to | A mock vendor master, reached through a mock intake queue by work-item id (hardened mode only) | Synthetic data. Not an authenticated intake; a real deployment needs a real source |
| What the downstream tools do | The tool server, called with a credential only the gateway holds | A compromised tool server is outside the guarantee |
| That events really happened | The signed, hash-chained audit log | It makes alteration, deletion or reordering detectable. It does not prove the entries were true, and truncation is only caught against an earlier chain head |

## 3. What happens when it is unclear (all fail closed)

- Unknown tool, ambiguous URL or path, malformed token, engine fault, audit write failure or slow audit write: the action is refused, and a restricted result is withheld.
- A held action (NEEDS APPROVAL) that nobody answers is a denial.
- The third policy block in a session freezes it and revokes its token. **Scope: that one session.** Other sessions, and other work items, are not affected, and a frozen session cannot be refreshed by OAuth. An attacker who can make an agent attempt three forbidden things can therefore end that session (see section 5, availability).
- Approvals are bound to a hash of session, tool and exact arguments, are one-time and expire; every other rule still runs after approval.

## 4. What the officer sees when asked

The approval request is built by the gateway from the tool name, the exact arguments and the rule's own words (for R7: that this session has read untrusted content, and from which tool). The agent cannot add an explanation. **Gap:** for a change to existing data the card does not yet show the old value beside the new one, and an officer who approves everything defeats R4 and R7 (approval fatigue). R7's workload is measured, not assumed; see the "approval workload" figure in the README.

## 5. The three goals, separately

| Goal | What exists | Evidence | Not covered |
|---|---|---|---|
| **Confidentiality** (restricted data does not leave) | R2 value matching, R3, R7, R8 (the Rule of Two, when the slip turns it on), R9 and secret detection, hardened mode | 0 of 41 supported disclosures reached the sink in our corpus; the real-model runs agree but are small | Paraphrase, spelled-out values, images (no OCR); a blind evaluation has not been done |
| **Integrity** (untrusted content cannot cause an invalid change) | R1 limits which tools run; R7 holds a consequential action after an untrusted read; R4 holds a bank-detail change | Rules are tested; **no integrity measurement exists** | Sentinel does not validate the proposed value. An approved change, or one inside an internal destination, is not checked for correctness |
| **Availability** (the agent keeps working) | R6 freezes only the offending session; budgets are per session | 0 of 28 valid actions wrongly blocked; R7 holds some valid ones (README) | An attacker who induces three blocks can freeze that session |

A confidentiality result does not imply the other two.

## 6. Routes outside the guarantee

Sentinel governs only what passes through the gateway. It does **not** govern:

- **The model's own reply** to the user. The gateway sees tool calls, not what the agent says in chat. In a hosted client such as Claude.ai, that reply goes to the client's provider.
- **Other capabilities the agent holds:** another MCP server, a browser, a direct credential, a local shell. For a real deployment the agent must hold no credential for what Sentinel is meant to govern. "Change one URL" is an integration benefit, not a guarantee.
- **Covert channels:** which calls the agent makes, their timing, retries, send versus no-send. Hardened mode narrows the e-mail channel to a fixed message, and the claim is only that: not that nothing can be inferred.
- **Several upstream servers:** one tool server per gateway is built.
- **Our tools are mocks.** No result here is evidence about real file, browser or database servers.

## 7. How each claim is evaluated

Measured from the mail sink, not from Sentinel's own verdicts, against a corpus **we wrote**, with the cases and their labels in `eval/`. Reported separately: disclosures that got through, declared gaps, redirects, valid actions wrongly blocked, valid tasks completed, and the approval workload. Mutation checks (`spikes/mutate.py`) show that each rule's tests can fail. An independent attempt by someone who has not read the rules has **not yet been made**; it will be reported on its own line, with the number of people and the date.
