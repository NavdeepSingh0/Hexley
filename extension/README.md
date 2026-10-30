# Sentinel Chrome Extension

Shows Sentinel's mascot on **claude.ai** and **chatgpt.com**, reacting to real gateway decisions as they happen. Lets you approve or deny held actions from the browser.

> **It does not enforce anything.** Sentinel's gateway does that. The extension only shows what Sentinel decided.

---

## Install (load unpacked)

1. Clone the Sentinel repo and check out `feat/extension`:
   ```bash
   git clone https://github.com/NavdeepSingh0/Sentinel.git
   cd Sentinel
   git checkout feat/extension
   ```

2. Copy the mascot file into the extension:
   ```bash
   bash extension/scripts/copy-mascot.sh
   ```

3. Open Chrome → `chrome://extensions` → enable **Developer mode** (top-right toggle).

4. Click **Load unpacked** → select the `extension/` folder inside the repo.

5. The Sentinel icon appears in your toolbar.

---

## Pairing with Sentinel

1. Start Sentinel:
   ```bash
   python -m pip install --user uv
   python -m uv sync
   npm --prefix site ci && npm --prefix site run build
   npm --prefix console ci && npm --prefix console run build
   python -m uv run python -m sentinel up --demo
   ```

2. Copy the full link it prints — looks like:
   ```
   http://127.0.0.1:8000/#token=hARp2Ku-JPSqzBdaWGdYZGCQ-...
   ```

3. Click the Sentinel toolbar icon → **Settings** → paste the full link → **Save & test**.

4. "Connected" appears — the mascot is now live.

---

## What the mascot shows

| State | Meaning |
|---|---|
| `sleeping` | No active Sentinel session |
| `idle` | Session active, waiting |
| `checking` | Evaluating an AI action |
| `allowed` | Action permitted (green, 1.5 s) |
| `denied` | Action blocked (blue) |
| `needs-approval` | Waiting for your decision (amber) |
| `quarantined` | Session frozen — too many violations |
| `verified` | Audit log confirmed intact |
| `tamper` | Audit log has been altered |

---

## Approving / denying held actions

When the mascot shows **needs-approval**:

1. A **Review** button appears on the mascot overlay.
2. Click it to see the tool, its arguments, and the time left.
3. **Approve** (requires a second click to confirm) or **Deny** (one click).
4. The result appears in the Sentinel console audit log.

---

## Permissions

| Permission | Why |
|---|---|
| `storage` | Saves your Sentinel address and token (session only by default) |
| `http://127.0.0.1/*` | Reach a locally-running Sentinel |
| `http://localhost/*` | Same |
| `https://claude.ai/*` | Inject the mascot overlay |
| `https://chatgpt.com/*` | Inject the mascot overlay |
| `https://*.trycloudflare.com/*` | Optional — for tunnel access (requested at runtime) |

**What this extension does NOT do:**
- Does not read your chat, prompts, or files
- Does not send any data anywhere except to your configured Sentinel address
- Does not enforce or block anything

---

## Updating the mascot

If `design/mascot/sentinel-mascot.js` is updated in the repo, re-copy it:

```bash
bash extension/scripts/copy-mascot.sh
```

Then reload the extension on `chrome://extensions`.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| "Not configured" | Open Settings and paste the Sentinel link |
| "Token rejected" | Restart Sentinel (`up --demo`) and paste the new link |
| "Sentinel not connected" | Make sure `sentinel up --demo` is running |
| Mascot not visible on claude.ai | Check that the site toggle is on in the popup |
| 409 on approve/deny | The approval expired or was already resolved — check the console |

