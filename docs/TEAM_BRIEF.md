# Sentinel: team brief (27 Oct 2026)

For the whole team. Part 1 is what exists and what we can honestly claim. Part 2 is a design request: **we need a mascot**.

## Part 1: where we are

**One line:** Sentinel sits between an AI agent and the tools it uses, and decides every action before it happens. The agent can do the job it was given and nothing else.

### The idea, in one example (our demo)
An officer gives an AI agent one job: *read a vendor's quotation, check our stock, and acknowledge it by e-mail.* The quotation contains a hidden paragraph asking the agent to put our secret depot stock in the reply. The agent follows it. Without Sentinel, the secret leaves the building. With Sentinel, the e-mail is stopped before it is sent. Every step the agent takes is individually allowed. Only the chain is the problem, and Sentinel watches the chain.

![Three columns: no protection, access control only, Sentinel](brief/console-comparison.png)

*Left two columns: the secret reaches the vendor (red). Right column: Sentinel stops it. The highlighted numbers and depot codes are exactly what it caught.*

### What is built and working (checked, not hoped)
| What | State |
|---|---|
| **The gateway**: checks every agent action against the officer's permission slip, six rules (R1 to R6), fails closed | Built. 310 automated tests pass |
| **Signed audit log**: every decision written down *before* the action runs, tamper-evident | Built. You can change one record and watch verification fail |
| **Officer approval**: risky actions (e.g. changing a vendor's bank account) wait for a human to approve that exact action | Built |
| **Hardened mode**: the agent cannot write free text at all, it can only trigger one fixed acknowledgement | Built |
| **Console**: the screens you see in this brief, with a guided demo order | Built, but it is the *minimum* version, not the final look |
| **Evaluation**: 31 different ways of hiding the secret in an e-mail (digits in other scripts, number words, dates, encodings...). Sentinel stopped **0 leaks out of 31**, while with no protection all 31 got through | Measured. Honest limit: we wrote the 31 cases ourselves, so this shows it does what we say, not that nothing else could slip past |
| **Real AI model test**: a real hosted model (NVIDIA nemotron) was fooled by the quotation in 13 of 13 usable runs without protection. With Sentinel, **0 of 9** leaked | Measured, but small samples and a rate-limited API (about 1 in 4 runs failed for that reason) |
| **A real chat client**: we connected **Claude.ai** to Sentinel through a public tunnel. When asked to include the secret stock figures in an e-mail, the e-mail was blocked and Claude told the user why | Worked on 27 Oct. A single run, not a measurement |

![Claude.ai being stopped by Sentinel](brief/real-claude-blocked-by-sentinel.png)

*A real Claude chat. "Used Sentinel, 1 failed": Sentinel refused the send, and Claude explains the reason to the user. Nothing was delivered.*

More screens: [the "why it was stopped" screen](brief/console-why-stopped.png), [the permission slip](brief/console-permission-slip.png), [officer approval](brief/console-officer-approval.png), [a frozen attacker](brief/console-freeze.png), [hardened mode](brief/console-hardened.png).

### Be careful what we say (so nobody gets caught out in Q&A)
- Sentinel is built for **MCP** (the standard way AI apps connect to tools). The deck's slide 6 also lists REST, browser, database, shell and cloud adapters. **Those are not built.** Say "designed for, MCP first".
- It only governs actions that go **through** it. An AI app with its own extra tools could leak around it. For our demos the agent only has Sentinel's tools.
- It does not control what the AI company sees of the data the agent reads.
- It catches the disguises we tested for. It does **not** catch a paraphrase such as "the western depot is well stocked". Hardened mode is our answer to that, and we show the gap openly.
- Real AI models sometimes ignore the hidden instruction by themselves (Claude did). Our point is that safety should not depend on that luck.
- Our numbers are one task, one scenario, a few models. Never say "100% secure".

### What we are planning next (not built yet)
1. **A new look** matching our deck: charcoal background, white bold lettering, spaced capital labels, thin lines, with a dark and an off-white theme.
2. **A chat page of our own** ("Sentinel Chat", a ChatGPT-style layout, clearly labelled as ours, using the nemotron model) so judges can type a prompt and watch Sentinel work.
3. **The mascot** (below).
4. Rehearsal, a fallback video of the demo, and the final deck numbers.

---

## Part 2: design request, the Sentinel mascot

We want a small animated character that lives in a corner of the console and of our chat page while Sentinel is working. It should be charming and make the demo memorable, but it must stay small and never cover the evidence.

### The rule that matters most
**The mascot never pretends.** Every reaction is triggered by something Sentinel really did. It is a living status light with a face, not decoration. Its short speech bubble is filled in from the real decision ("Checking the stock register", "That would send secret data out, so I stopped it").

### Look
- **Blocky pixel-art, 2D**, simple enough to draw on a small grid (suggest **24 x 24 or 32 x 32 pixels**, shown 2 to 4 times bigger without blurring).
- It should suit our deck: calm, serious, a little friendly. Think **guard, sentry or gatekeeper**: a helmet or cap, a clipboard (the permission slip), a small shield, a lantern, a badge. Your call on the character.
- **Original.** Please do not copy Claude's mascot, Minecraft characters (Steve, Creeper), or any known mascot or logo. "Blocky pixel style" is fine; a lookalike is not.
- **Colour:** mostly off-white and greys with a thin dark outline so it reads on both a charcoal background and an off-white one. **Avoid red on the body**: in our screens red means "real harm reached the outside", and blue means "stopped by Sentinel". A small accent is fine.
- Give it a **name** if one comes to mind.

### Poses we need (each one 2 to 4 frames so it moves)
| # | When it shows | Idea |
|---|---|---|
| 1 | **Idle / watching**: Sentinel is running, nothing happening | Gentle bob or blink, scanning side to side |
| 2 | **Checking**: an agent action is being evaluated | Looking at the clipboard, or lantern sweeping |
| 3 | **Allowed**: the action was fine (neutral, never a celebration) | A small nod or tick |
| 4 | **Stopped**: Sentinel blocked something | Hand or shield up, firm |
| 5 | **Frozen**: the agent was quarantined after repeated attempts | Padlock, or a freeze or ice look, the strongest pose |
| 6 | **Waiting for the officer**: an action needs human approval | Holding up the slip, tapping a foot |
| 7 | *(optional)* **Log verified** | A stamp or seal |
| 8 | *(optional)* **Tamper alarm**: the audit log was altered | Alert, flashing |

Also useful: a **sleeping** pose for when no agent is connected.

### What to hand back
- **Sketches first**: a photo of paper is fine. Tell us your idea before polishing.
- Then pixel art as **PNG files with a transparent background**, one image per pose with the frames side by side, or one image per frame. Piskel (free, in the browser), Aseprite, Figma or anything you like works. Please do not blur or anti-alias: crisp pixels.
- Include the **character on its own at large size** too (for the deck).

### Dates (suggested)
- **Wed 28 Oct, evening:** first sketches or a rough idle pose.
- **Thu 29 Oct, midday:** the finished set, so there is time to build it into the console before the on-site build starts on **Fri 30 Oct at 12:00**.

If something here is unclear or you have a better idea for the character, tell us. The poses and the "never pretends" rule are the fixed part; everything else is yours.
