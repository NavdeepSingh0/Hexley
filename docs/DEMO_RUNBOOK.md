# Demo runbook, round 2

> **The name:** the product is now Hexley (`hexley.site`). The program's command (`python -m sentinel`), the repository and the code keep the old name until after judging, and recorded proof files say Sentinel because that is what was said then. If asked: "We renamed it this week; the code follows after the finale."

31 Oct 2026. Everything here was checked against the running program. Quote only the numbers in section 4, with their "n". If a number is not in this file, do not say it.

## 1. Before you go on (30 minutes ahead)
**The hosted site is `https://hexley.site`** (AWS, Sydney). It serves the website, console, API and gateway. To open the console you need the officer token; print it in your own terminal, never on the projector:
```
ssh -i $env:USERPROFILE\.ssh\hexley.pem ubuntu@54.79.105.94 "sudo grep SENTINEL_API_TOKEN /etc/hexley/hexley.env"
```
Then open `https://hexley.site/#token=<that token>`. From India the first load is slow: open every page you will show once beforehand, so the browser has cached them.

**A restart of the server logs out every AI client and session.** Do not redeploy on the morning of the demo.

**Local fallback, if the hosted site or the network fails** (the folder is the repository, the same one as always):
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
SAY: "Agents can already act: send e-mail, read databases, edit files. The risk is not a hacker breaking in. It is one poisoned document in the pile that tells the agent to do something the task never asked for. Every call the agent makes can be individually allowed and the chain still leaks. Hexley limits the agent to the job a person approved. We limit what it *does*, not how it thinks, so the agent is not made dumber. No AI makes any security decision in Hexley: the rules are ordinary code."
DO: click **See it work**.

**0:40 Situation 1: the poisoned quotation (1 min 30).**
DO: `Enter`. The officer's permission slip appears (the task, the tools, where it may send, a message limit). `Enter` to confirm.
SAY: "Before the agent reads anything, a person approves this slip. This is the task."
Three columns run the same agent. It is a replay of a **real recorded run of a real model**, with Hexley's decisions computed live.
SAY: "Left: no protection. The stock figures leaked. Middle: normal access control. Every call was allowed, and it still leaked: the agent had the right to read the stock and the right to send e-mail. Right: Hexley. It stopped the e-mail that carried restricted data, and the vendor still got a clean acknowledgement. The work continued."
DO: `Enter` to open the verdict; read the plain-English reason (rule R2: this e-mail would carry restricted data outside).
SAY: "The reason is one sentence a non-technical officer can read. The agent itself is only told 'blocked, send it without that information': we never tell it what matched, so an attacker cannot learn what to reword."

**2:10 Situation 2: a persistent attacker is frozen (45 s).**
SAY: "A compromised agent keeps trying. Two refused attempts are normal. The third freezes the session and revokes its token. Nothing more gets through."

**2:55 Situation 3: the paraphrase, and the hardened mode (1 min).** Say the weakness yourself before anyone asks.
SAY: "Here is our honest limit. Hexley recognises restricted values by what they are. If the agent paraphrases ('plenty of stock at the western depot'), that passes value matching. It is a declared gap. Two answers: hardened mode, where the agent cannot compose a message at all, only name a quotation, and Hexley writes a fixed message and chooses the recipient (right lane: its attempts are blocked and it is frozen). And a slip setting we call the Rule of Two: once a session has read restricted data and untrusted content, anything sent outside waits for the officer."

**3:55 Situation 4: a bank-detail change needs the officer (45 s).**
SAY: "Some actions should never run on the agent's word. A change to where money goes is held. The officer sees the exact request, and approves or denies that one request, once. Silence is a denial."
DO: approve it in the console card.

**4:40 The receipts (1 min).** After the last situation the receipts screen appears.
DO: press `V`: the log verifies.
SAY: "Every decision is written to a signed, hash-chained log *before* anything is forwarded."
DO: press `T` (tamper), then `V`: the check turns red at the record that was changed. Press `R` to restore.
SAY: "Change one record, delete one, reorder two: verification fails and says where. What it does not do is prove the events were true, and a truncated log is only caught if the verifier holds an earlier head."

**5:40 Close (20 s).**
SAY: "Tested: about 1,050 automated tests, a labelled corpus, 30 recordings of a real model, real clients. Not done: a blind attacker and an adaptive attacker. Our limits are on the next page of the site, because a security tool that hides its limits is not one."

## 2B. Real connectors (about 2 minutes, after section 2)
SAY: "That was our own demo tools. This is the real thing. Hexley does not rebuild Gmail or Slack and does not hold their passwords: Claude keeps its own connectors, and Hexley only decides whether each call may run."

Show one of these, whichever you rehearsed. Each ran on real accounts on 31 Oct, once per condition.
- **Claude Code with Claude's own Gmail, Slack and Notion:** a send to an address not on the slip is refused before it reaches the service, and the honest one goes through.
- **Antigravity with GitHub's own server:** an issue carries hidden steps to comment on a private repository. The read works, the comment is refused with Hexley's own sentence, and the private repository stays untouched.

**Say this before anyone asks:** "In these attack runs we told the AI to follow the planted steps, as a stand-in for a fooled model. The models we tested ignored the plain injection by themselves, so this shows Hexley's refusal, not a model being tricked."

## 3. Optional extras (each 1 to 2 minutes; pick by time and by what you rehearsed)
**A. Not tied to one task: Hexley Chat, electoral office (90 s).** Open `/chat`, pick **Electoral office: a compromised circular**, mode **Scripted attacker**, confirm the slip, send.
SAY: "No quotations, no stock. A district office summarises circulars for the chief electoral officer. One circular hides an instruction to e-mail the whole voter roll to an address only it names. The same rules: the e-mail is denied, the real summary still goes. This is the local-AI case the SIH problem statements ask for: with a local model, nothing leaves the building, and Hexley limits what the agent can do with what it reads."
Honest limit to say if asked: names with a short address, without an ID or phone, are not fingerprinted (declared gap).

**B. Your own PDF, live (2 min; only if rehearsed).** Pick **Work with your own document**, upload a PDF with the **+** button, mode **Live model**. Open **Details** to show "what the model was given", including hidden text.
SAY: "The model never sees the file by magic: it reads it through a tool, so Hexley knows the session has read untrusted content, and from that moment anything sent outside waits for the officer."
**Be ready for "nothing happened".** Modern models often ignore a note that merely sits in a document (Claude did in the two runs we saw; the hosted model did in 5 of 5 runs of our own summarise prompt). Say so: "When the model ignores it there is nothing to stop. When the task says 'carry out the document's steps', the model we tested acted on it in 4 of 5 runs, and Hexley stopped every attempt to send anything outside." (Section 4 has the counts.)

**C. Other connectors in the same chat (1 min, say it; show the docs page).** Open `/docs/connect-claude-code-hook`.
SAY: "A gateway only decides what goes through it. If a user also has Gmail switched on in the same chat, or attaches a file, Hexley does not see that. We say it plainly. For clients that support hooks, like Claude Code, the client itself asks Hexley before every tool call, whichever server the tool belongs to, and a Hexley that is down blocks the call. We ran five real Claude Code sessions: the same over-share that was delivered with no hook was denied with it, and the tool never ran. One session per condition, not a measurement."

**D. Claude.ai, where there is no hook (2 min; the connect flow itself is the point).** In Claude.ai add the custom connector `https://hexley.site/mcp`: Google's account picker, one Allow page, back in Claude. The exact request to set it up is on the Connect page, with a copy button; Claude lists its own tools and replies with the text and where it goes: initials, Settings, Your Claude, Instructions. Start a new chat after saving. **Reconnect before you go on, because a server restart signs you out.** To show a refusal, ask Claude to mail an address that is not on the slip: it asks first, Hexley refuses (R1), no mail goes. If a call is held instead, the card with the exact request appears in the console.
SAY: "On Claude.ai a connector runs on the vendor's servers and nothing asks us, so this route is advisory. The text tells Claude to ask Hexley first. Nothing forces it to, and a hidden instruction can try to talk it out of it. We ran it on one account, once per test: it asked first each time, an outsider send was refused and did not go, and an honest send went. In Claude Code, with no hook and n=5 per condition, it asked first in every run with the text and obeyed every no."

**E. The browser extension (only if the signed-in claude.ai page was checked).** Load the `extension/` folder unpacked, paste the link into its Settings. It shows the mascot on claude.ai reacting to real decisions and lets the officer approve from the browser. It enforces nothing. It was tested in a real browser on claude.ai's check page, **not on a signed-in page**: look at it before you show it.

## 4. Numbers you may say (always with the "n")
| What | Number | Say it like this |
|---|---|---|
| Scripted corpus, restricted data that got past Hexley | **0 of 43** (95% interval 0 to 8%); the same cases with no protection: 43 of 43 | "On 43 cases that **we wrote**, none got through. It shows it does what its documentation says, not that an attacker cannot find another route." |
| Declared gaps | **6 of 6** got through | "Six cases we know it misses, listed on the limits page." |
| Valid actions wrongly blocked | **0 of 28** (interval 0 to 12%) | "In 10 clean tasks, none of 28 valid actions was blocked." |
| Real model, poisoned quotation, no protection | **13 of 13** lanes leaked | "One model, one task. 21 of 90 lanes failed on the hosted API and are excluded." |
| Real model, behind Hexley | **0 of 9** lanes leaked (interval 0 to 30%) | "A small sample: a count with an interval, not a guarantee." |
| Live runs on 29 Oct, a hosted model, 5 runs per family | Task says "follow the document": the model acted on the hidden note **4 of 5**; Hexley refused all 3 supplier e-mails and held then denied all 3 status posts; a copy into the internal `/out` folder was allowed | "The one thing that got through is by design: `/out` is a folder the officer named internal." |
| Same, task is only 'summarise' | The model followed the note **0 of 5** | "Then there is nothing to stop. That is a result too." |
| Real Claude Code sessions with the hook | 5 sessions, one per condition: over-share delivered with no hook, **denied (R2) with it**, unreachable hook blocked the tool | "One session per condition, a demonstration." |
| Approval cost | R7 held **3 of 12** valid sends after an untrusted read | "The price of the rule is approvals; we report it." |
| Speed (one laptop, loopback, mock tools) | a decision takes 7.5 to 140 microseconds; writing the signed record about 2 ms; a whole check 6 to 11 ms (p50) | "The checks are not the cost. A call through our gateway takes about 50 to 85 ms, mostly the proxy library, and we have not profiled the rest. This is not a scale claim." |
| Matcher on generated variants | **775 of 775** documented ways of writing a value recognised; **0 of 400** ordinary sentences wrongly flagged | "31 ways of writing a value, written by us. The benchmark also found four ways we had missed; we closed them." |
| Incident-shaped scenarios | of 20 harmful steps: **13 refused, 6 held for the officer, 1 not stopped** (the paraphrase gap); of 20 benign steps: **19 allowed, 1 held, 0 wrongly refused** | "15 scenarios in the shape of reported incidents: our own, synthetic data, not the original exploits." |
| How many of 28 reported incidents | **about 12 to 18 of 28 (43 to 64 percent)** in the complete state, 11 today; **10 are out of reach by design** (browser agents, supply chain, server-side) | "A counterfactual reading by us, and only where the agent's calls pass through Hexley. Most of those incidents happened inside closed products." |
| Real connectors through Hexley, 31 Oct | Gmail, Slack and Notion through Claude's own connectors in Claude Code; GitHub's own server in Antigravity. **Real send, attack refused, honest task running: one run per condition** | "A demonstration on test accounts. In the attack runs the AI was told to follow the planted steps; no model was actually fooled." |
| Is it told, does it ask? (Claude Code, **no hook**, not Claude.ai) | With the preferences text it asked Hexley first in **5 of 5** runs on each of 2 models, also when a mail said to skip it; without the text **0 of 5**; when Hexley said no, the send did not run in **10 of 10** (about 72 to 100%) | "Both models ignored that injection with no Hexley at all, so we do not claim this stopped an attack. Advisory, and not measured on Claude.ai." |
| Claude Code in the real VS Code window, Gmail, 31 Oct | **One run per test:** honest send allowed and sent; send off the slip blocked (R1); a poisoned mail read, with **no send attempted**, and that send asked directly at the decision endpoint blocked (R1, R2, R3) | "Hexley stopped nothing in the window on that attack, because Claude did not try. We asked the decision directly. A demonstration, not a rate." |
| Field test, the team's 5 documents, 31 Oct | **64 sensitive fields, 8 writings each:** as written 57 refused by value, 7 held, **0 let through in any writing**; all 21 secrets refused outside. Cost: 12 of 34 harmless fields refused | "Documents and labels we wrote, no real attacker. Held depends on the officer reading it. The first run found holes in GitHub and base64, and we fixed them." |
| Claude.ai with the preferences text, 31 Oct | **One account, one run per test:** asked first each time; an outsider send refused (R1) and not sent; an honest send allowed and sent; a poisoned mail read, with no attempt on its hidden steps | "A demonstration, not a rate. Advisory: nothing forces it to ask, and we did not try an instruction to skip Hexley on Claude.ai." |
| Tests | about 1,050 automated tests, plus 149 for the console and 72 for the website (see the last row of `docs/PHASE_LOG.md`) | |

## 5. Likely questions
- **"How is this different from AWS Cedar and Microsoft FIDES?"** See `docs/research/DIFFERENCES_CEDAR_FIDES.md` (30-second answer inside). Short: they are good and we use their ideas. Cedar's AgentCore Policy decides on the caller, the tool and its parameters inside AWS's gateway (and now has session-aware policies you write per pattern); FIDES labels data inside agents built with Microsoft's framework. Hexley sits outside the agent, so it works with agents nobody can modify, and its input is the task a person approved plus what the session read. We have no formal guarantee and do not hide data from the model yet. They have bigger evaluations. Never say "nothing like this exists".
- **"Why not just tell the model not to leak?"** "An instruction is advice a poisoned document can talk it out of. Our unprotected lanes leaked in every usable run." (13 of 13, section 4.)
- **"Why not another AI to judge the actions?"** "A judge can be talked into things by the same text. Research on adaptive attacks keeps breaking classifiers. Hexley's decision is ordinary code you can read and test."
- **"Is it a guarantee?"** "No. A measurement on cases we wrote, plus a list of routes it does not cover. The blind red team and an adaptive attacker are still to be done."
- **"What if the model just ignores the attack?"** "Then there is nothing to stop, and that happens with strong models. Two things remain: weaker or local models follow injections (a hosted model did, 4 of 5), and even with no attack the helpful agent over-shares: in our clean quotation runs 4 of 13 unprotected lanes sent the restricted figures anyway."
- **"Does it make the agent dumber?"** "It limits actions, not thinking. 0 of 28 valid actions blocked in our clean tasks; some valid sends wait for the officer, and we report how many."
- **"Does the model provider see our data?"** "Yes: what the agent reads goes to its model. Hexley guards the exits. Two answers: a local model (it runs on your computer through Ollama in Hexley Chat), and replacing restricted values with placeholders so the model never sees them, which is planned, not built."
- **"Who is the customer?"** "Offices that run agents on sensitive records: government departments (the SIH local-AI problems), finance, health. The officer is the person who approves the task."
- **"Does it work with ChatGPT, Gmail, GitHub, VS Code?"** "Gmail, Slack and Notion through Claude's own connectors in Claude Code, Gmail again in Claude Code inside the real VS Code window, and GitHub's own server in Antigravity: run on real test accounts, once per condition. VS Code's own MCP route and Copilot are not run. Enforced where the client has a hook. Claude.ai has no hook, so that route is advisory. ChatGPT: not tested."
- **"What about Antigravity's terminal?"** "Not judged. Its MCP tools go through our hook; `git` in its terminal does not. And it does not show us what a tool returned, so we cannot do the data check there. We say so."
- **"What did your teammate see, the bounced e-mail?"** "Most likely a real mail through ChatGPT's own connector; we have not confirmed the route. Hexley has no code that sends real mail from that route, so it did not go through us. That is the whole point: a direct connector goes around any gateway, so the demo account must only use the route we judge."
- **"Can I try it myself, now?"** "Yes. Open `hexley.site`: the demo and the chat, live model included, need no account. They use synthetic data and mock tools. Real connector approvals, the tamper demo and uploads stay with the officer. Only one console demo runs at a time, so you may be asked to retry, and the live model has a limited share for visitors."
- **"Can anyone sign in with Google?"** "Yes, any Google account, and for now everyone shares one slip. There is a limit per address, which slows one noisy address and does nothing against many. Separate slips per person are future work."
- **"Is it production-ready?"** "No. Identity is one token, state is in memory, and a restart of the hosted server clears its log. The product roadmap lists what is left: storage that survives a restart, officer sign-in and roles, a phone approval page, an audit export, packaging."
- **"Pricing?"** "The pricing page is illustrative. Nothing is offered or sold."

## 6. Never say
"100 percent secure", "unbreakable", "nothing like this exists", "works with every AI", "tested with ChatGPT", "enforced on Claude.ai" (it is advisory there), "Hexley stopped a fooled model" (none was), "all 18 tool-call incidents", "75 percent", "Hindi interface", "phone approval" (the card is in the console, not a phone page), "we beat Cedar/FIDES", any rate without its n, or that the live model "always" follows the attack.

## 7. If something goes wrong
| Problem | Do |
|---|---|
| "The access token is missing or wrong" | Open the link the command printed in a **fresh tab** (or add `/console/#token=…` yourself). |
| "port in use" at start | Add `--api-port 8010 --gateway-port 8110` (and keep `--tools-port 8300`). |
| Live model slow or errors | Switch to **Scripted** or **Replay**. Say: "The hosted model is rate-limited; the decisions are the same code." |
| No Wi-Fi | Everything in section 2 works offline. Skip the live model, Claude.ai and the tunnel. |
| Console frozen or blank | Press `F5`; if the token message returns, open the printed link again. |
| A judge types a new attack | "Good: that is the blind test we have not run yet. Try it in Scripted mode and we will show what is decided and why." |
| `hexley.site` is down or very slow | Use the local fallback in section 1. Say: "Same program on this laptop." |
| An AI client says it needs to sign in again | The server restarted. Reconnect: Google, then Allow. An Antigravity hook also needs a new token. |
| A send seems stuck on "ask the officer" | Open the console with the officer's link. The card shows the exact request; approve or deny it, and the same call then runs once. |
| "Too many requests from this address" | One address went over a limit (30 sign-in requests a minute; for a visitor, 6 chat messages a minute). Wait one minute. Everyone on the same hall Wi-Fi may count as one address, so use your officer link on stage: it is not limited this way. |
| A visitor's demo is running when you start yours | Nothing to do: your run ends theirs. |
| AWS account restricted (the identity check had failed) | Local fallback for today; Render is the hosting backup (`docs/DEPLOY.md`). |
| A connector asks to log in | Reconnect it in Claude's connector settings, on the **test** account. |
