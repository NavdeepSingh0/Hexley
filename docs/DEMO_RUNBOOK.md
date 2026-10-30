# Demo runbook, round 2

30 Oct 2026. Everything here was checked against the running program today. Quote only the numbers in section 4, with their "n". If a number is not in this file, do not say it.

## 1. Before you go on (30 minutes ahead)
**Start it** (the folder is the repository, the same one as always):
```
cd "C:\Projects\zinnovatio 4.0\sentinel"
python -m uv run python -m sentinel up --demo --tools-port 8300
```
- `--tools-port 8300` matters: port 8200 is used by your other project (`eupay-link`), and the default would stop with "port in use". If it says another port is busy, add `--api-port 8010 --gateway-port 8110`.
- It opens the website in your browser with the officer token in the link. **Use that tab.** If you open a new tab, paste the printed link again (the token lives per tab). The console is at the same address followed by `/console/`.
- `--demo` starts a fresh audit log every time and turns on the tamper button, so a rehearsal can never stop the real demo.
- The live model uses the key in your `.env` in this folder (never on screen). The first live answer can take 30 to 60 seconds.

**Checklist**
- [ ] The tab opened by the command shows the home page; click **See it work** and the console loads with the purple "Run the guided demo" button (no red token message).
- [ ] Press `?` in the console: the presenter keys appear. Press `Esc`.
- [ ] Press `Enter` once to run through a full guided demo as a rehearsal, then restart the command for a clean log.
- [ ] Phone on hotspot, laptop charged, notifications off, browser at 100 percent zoom, dark theme (projector: try Light if the room is bright; the **Light** button is top right).
- [ ] A second tab open on the docs page **Questions judges ask** (`/docs/faq`, it has the Cedar and FIDES answer) and one on **Limits and honest scope** (`/docs/limits`).
- [ ] `docs/research/DIFFERENCES_CEDAR_FIDES.md` open on your phone, for round-2 questions.
- [ ] Do **not** start the Claude.ai tunnel or the Claude Code hook unless you will show them (section 3).

**Presenter keys in the console:** `Enter` next step, `N` skip to the next situation, `V` verify the log, `T` tamper with one record, `R` restore it, `?` help, `Esc` close.

## 2. The main demo: 6 minutes, only the console
The guided demo is four situations. Press `Enter` to advance.

**0:00 Opening (on the home page, 30 s).**
SAY: "Agents can already act: send e-mail, read databases, edit files. The risk is not a hacker breaking in. It is one poisoned document in the pile that tells the agent to do something the task never asked for. Every call the agent makes can be individually allowed and the chain still leaks. Sentinel limits the agent to the job a person approved. We limit what it *does*, not how it thinks, so the agent is not made dumber. No AI makes any security decision in Sentinel: the rules are ordinary code."
DO: click **See it work**.

**0:40 Situation 1: the poisoned quotation (1 min 30).**
DO: `Enter`. The officer's permission slip appears (the task, the tools, where it may send, a message limit). `Enter` to confirm.
SAY: "Before the agent reads anything, a person approves this slip. This is the task."
Three columns run the same agent. It is a replay of a **real recorded run of a real model**, with Sentinel's decisions computed live.
SAY: "Left: no protection. The stock figures leaked. Middle: normal access control. Every call was allowed, and it still leaked: the agent had the right to read the stock and the right to send e-mail. Right: Sentinel. It stopped the e-mail that carried restricted data, and the vendor still got a clean acknowledgement. The work continued."
DO: `Enter` to open the verdict; read the plain-English reason (rule R2: this e-mail would carry restricted data outside).
SAY: "The reason is one sentence a non-technical officer can read. The agent itself is only told 'blocked, send it without that information': we never tell it what matched, so an attacker cannot learn what to reword."

**2:10 Situation 2: a persistent attacker is frozen (45 s).**
SAY: "A compromised agent keeps trying. Two refused attempts are normal. The third freezes the session and revokes its token. Nothing more gets through."

**2:55 Situation 3: the paraphrase, and the hardened mode (1 min).** Say the weakness yourself before anyone asks.
SAY: "Here is our honest limit. Sentinel recognises restricted values by what they are. If the agent paraphrases ('plenty of stock at the western depot'), that passes value matching. It is a declared gap. Two answers: hardened mode, where the agent cannot compose a message at all, only name a quotation, and Sentinel writes a fixed message and chooses the recipient (right lane: its attempts are blocked and it is frozen). And a slip setting we call the Rule of Two: once a session has read restricted data and untrusted content, anything sent outside waits for the officer."

**3:55 Situation 4: a bank-detail change needs the officer (45 s).**
SAY: "Some actions should never run on the agent's word. A change to where money goes is held. The officer sees the exact request, and approves or denies that one request, once. Silence is a denial."
DO: approve it in the console card.

**4:40 The receipts (1 min).** After the last situation the receipts screen appears.
DO: press `V`: the log verifies.
SAY: "Every decision is written to a signed, hash-chained log *before* anything is forwarded."
DO: press `T` (tamper), then `V`: the check turns red at the record that was changed. Press `R` to restore.
SAY: "Change one record, delete one, reorder two: verification fails and says where. What it does not do is prove the events were true, and a truncated log is only caught if the verifier holds an earlier head."

**5:40 Close (20 s).**
SAY: "Tested: about 750 automated tests, a labelled corpus, 30 recordings of a real model, real clients. Not done: a blind attacker and an adaptive attacker. Our limits are on the next page of the site, because a security tool that hides its limits is not one."

## 3. Optional extras (each 1 to 2 minutes; pick by time and by what you rehearsed)
**A. Not tied to one task: Sentinel Chat, electoral office (90 s).** Open `/chat`, pick **Electoral office: a compromised circular**, mode **Scripted attacker**, confirm the slip, send.
SAY: "No quotations, no stock. A district office summarises circulars for the chief electoral officer. One circular hides an instruction to e-mail the whole voter roll to an address only it names. The same rules: the e-mail is denied, the real summary still goes. This is the local-AI case the SIH problem statements ask for: with a local model, nothing leaves the building, and Sentinel limits what the agent can do with what it reads."
Honest limit to say if asked: names with a short address, without an ID or phone, are not fingerprinted (declared gap).

**B. Your own PDF, live (2 min; only if rehearsed).** Pick **Work with your own document**, upload a PDF with the **+** button, mode **Live model**. Open **Details** to show "what the model was given", including hidden text.
SAY: "The model never sees the file by magic: it reads it through a tool, so Sentinel knows the session has read untrusted content, and from that moment anything sent outside waits for the officer."
**Be ready for "nothing happened".** Modern models often ignore a note that merely sits in a document (Claude did in the two runs we saw; the hosted model did in 5 of 5 runs of our own summarise prompt). Say so: "When the model ignores it there is nothing to stop. When the task says 'carry out the document's steps', the model we tested acted on it in 4 of 5 runs, and Sentinel stopped every attempt to send anything outside." (Section 4 has the counts.)

**C. Other connectors in the same chat (1 min, say it; show the docs page).** Open `/docs/connect-claude-code-hook`.
SAY: "A gateway only decides what goes through it. If a user also has Gmail switched on in the same chat, or attaches a file, Sentinel does not see that. We say it plainly. For clients that support hooks, like Claude Code, the client itself asks Sentinel before every tool call, whichever server the tool belongs to, and a Sentinel that is down blocks the call. We ran five real Claude Code sessions: the same over-share that was delivered with no hook was denied with it, and the tool never ran. One session per condition, not a measurement."

**D. The Claude.ai connector (only if you tested it today).** Command: `python -m uv run python -m sentinel up --demo --tunnel --oauth-preset own_document --tools-port 8300`. In Claude.ai add the printed address as a custom connector, choose Sign in now, and type the six-digit officer code from the terminal. Switch Gmail and other connectors **off**. Tested once on a free account on 27 Oct. If anything fails, show `/integrations` instead: it has the recorded evidence.

**E. The browser extension (only if the signed-in claude.ai page was checked).** Load the `extension/` folder unpacked, paste the link into its Settings. It shows the mascot on claude.ai reacting to real decisions and lets the officer approve from the browser. It enforces nothing. It was tested in a real browser on claude.ai's check page, **not on a signed-in page**: look at it before you show it.

## 4. Numbers you may say (always with the "n")
| What | Number | Say it like this |
|---|---|---|
| Scripted corpus, restricted data that got past Sentinel | **0 of 43** (95% interval 0 to 8%); the same cases with no protection: 43 of 43 | "On 43 cases that **we wrote**, none got through. It shows it does what its documentation says, not that an attacker cannot find another route." |
| Declared gaps | **6 of 6** got through | "Six cases we know it misses, listed on the limits page." |
| Valid actions wrongly blocked | **0 of 28** (interval 0 to 12%) | "In 10 clean tasks, none of 28 valid actions was blocked." |
| Real model, poisoned quotation, no protection | **13 of 13** lanes leaked | "One model, one task. 21 of 90 lanes failed on the hosted API and are excluded." |
| Real model, behind Sentinel | **0 of 9** lanes leaked (interval 0 to 30%) | "A small sample: a count with an interval, not a guarantee." |
| Live runs on 29 Oct, a hosted model, 5 runs per family | Task says "follow the document": the model acted on the hidden note **4 of 5**; Sentinel refused all 3 supplier e-mails and held then denied all 3 status posts; a copy into the internal `/out` folder was allowed | "The one thing that got through is by design: `/out` is a folder the officer named internal." |
| Same, task is only 'summarise' | The model followed the note **0 of 5** | "Then there is nothing to stop. That is a result too." |
| Real Claude Code sessions with the hook | 5 sessions, one per condition: over-share delivered with no hook, **denied (R2) with it**, unreachable hook blocked the tool | "One session per condition, a demonstration." |
| Approval cost | R7 held **3 of 12** valid sends after an untrusted read | "The price of the rule is approvals; we report it." |
| Tests | about 750 automated tests (749 passed at the last full run) | |

## 5. Likely questions
- **"How is this different from AWS Cedar and Microsoft FIDES?"** See `docs/research/DIFFERENCES_CEDAR_FIDES.md` (30-second answer inside). Short: they are good and we use their ideas. Cedar's AgentCore Policy decides on the caller, the tool and its parameters inside AWS's gateway (and now has session-aware policies you write per pattern); FIDES labels data inside agents built with Microsoft's framework. Sentinel sits outside the agent, so it works with agents nobody can modify, and its input is the task a person approved plus what the session read. We have no formal guarantee and do not hide data from the model yet. They have bigger evaluations. Never say "nothing like this exists".
- **"Why not just tell the model not to leak?"** "An instruction is advice a poisoned document can talk it out of. Our unprotected lanes leaked in every usable run." (13 of 13, section 4.)
- **"Why not another AI to judge the actions?"** "A judge can be talked into things by the same text. Research on adaptive attacks keeps breaking classifiers. Sentinel's decision is ordinary code you can read and test."
- **"Is it a guarantee?"** "No. A measurement on cases we wrote, plus a list of routes it does not cover. The blind red team and an adaptive attacker are still to be done."
- **"What if the model just ignores the attack?"** "Then there is nothing to stop, and that happens with strong models. Two things remain: weaker or local models follow injections (a hosted model did, 4 of 5), and even with no attack the helpful agent over-shares: in our clean quotation runs 4 of 13 unprotected lanes sent the restricted figures anyway."
- **"Does it make the agent dumber?"** "It limits actions, not thinking. 0 of 28 valid actions blocked in our clean tasks; some valid sends wait for the officer, and we report how many."
- **"Does the model provider see our data?"** "Yes: what the agent reads goes to its model. Sentinel guards the exits. Two answers: a local model (it runs on your computer through Ollama in Sentinel Chat), and replacing restricted values with placeholders so the model never sees them, which is planned, not built."
- **"Who is the customer?"** "Offices that run agents on sensitive records: government departments (the SIH local-AI problems), finance, health. The officer is the person who approves the task."
- **"Does it work with ChatGPT, Gmail, GitHub?"** "Claude.ai through sign-in and Claude Code through a token or the hook: tested once each. ChatGPT: not tested. GitHub and Gmail as protected connectors: next on the roadmap, not built."
- **"Is it production-ready?"** "No. Identity is one token, state is in memory. The product roadmap lists what is left: storage that survives a restart, officer sign-in and roles, a phone approval page, an audit export, packaging."
- **"Pricing?"** "The pricing page is illustrative. Nothing is offered or sold."

## 6. Never say
"100 percent secure", "unbreakable", "nothing like this exists", "works with every AI", "tested with ChatGPT/Gmail/GitHub", "Hindi interface", "phone approval" (the card is in the console, not a phone page), "we beat Cedar/FIDES", any rate without its n, or that the live model "always" follows the attack.

## 7. If something goes wrong
| Problem | Do |
|---|---|
| "The access token is missing or wrong" | Open the link the command printed in a **fresh tab** (or add `/console/#token=…` yourself). |
| "port in use" at start | Add `--api-port 8010 --gateway-port 8110` (and keep `--tools-port 8300`). |
| Live model slow or errors | Switch to **Scripted** or **Replay**. Say: "The hosted model is rate-limited; the decisions are the same code." |
| No Wi-Fi | Everything in section 2 works offline. Skip the live model, Claude.ai and the tunnel. |
| Console frozen or blank | Press `F5`; if the token message returns, open the printed link again. |
| A judge types a new attack | "Good: that is the blind test we have not run yet. Try it in Scripted mode and we will show what is decided and why." |
| The hosted site (Render, Vercel) | Not part of this demo: it had errors and will be redeployed later. Do not open it on stage. |
