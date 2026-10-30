# Browser extension plan

For the teammate who builds Sentinel's browser extension during the finale build (Fri 30 Oct to Sat 31 Oct 2026).

**Deadlines.** E0 is shown to Navdeep by **Fri 17:00**. E1 and E2 are merged by **Sat 06:00**. Polish lands by **Sat 08:00**. Code freeze is Sat 10:00 and judging is Sat 14:00.

---

## 1. What it is, and what it is not
- **The problem it solves.** When someone uses Claude.ai with the Sentinel connector, Sentinel decides every Sentinel tool call: allowed, denied, needs the officer's approval, or quarantined. Today those decisions are visible only in Sentinel's console, in another tab.
- **What it does.**
  - It shows Sentinel's mascot on claude.ai and chatgpt.com, reacting to Sentinel's real decisions as they happen.
  - It lets the officer approve or deny a held action from the browser.
- **What it does not do: enforce anything.** Sentinel enforces at the gateway. The extension only shows what Sentinel decided, so it must never say or suggest that it blocked something itself.
- **It reads nothing from the pages it sits on (E0 to E3).** It does not read the chat, the prompt or the files. Reading the page would be a privacy decision Navdeep makes, and only in E4.

## 2. Run the backend
```
git clone https://github.com/NavdeepSingh0/Sentinel.git
cd Sentinel
python -m pip install --user uv
python -m uv sync
npm --prefix site ci && npm --prefix site run build
npm --prefix console ci && npm --prefix console run build
python -m uv run python -m sentinel up --demo
```
- **The link.** `up` prints a link like `http://127.0.0.1:8000/#token=...`. The part after `#token=` is the **officer token**. Every API call needs the header `Authorization: Bearer <token>`.
- **Making real decisions happen without Claude.ai:**
  1. Open the link `up` printed (it signs the site in), then go to Chat.
  2. Pick "Process a vendor quotation", choose "Scripted attacker (no model)", confirm the slip and send a message.
  3. The gateway denies the leaking e-mail. The mascot state becomes `denied`.
- **For a held action:** the "Update a vendor's bank details" task asks for the officer's approval.
- **With a real Claude.ai session:** Navdeep runs `up --tunnel` and connects Claude.ai. The same endpoints then carry those decisions.

## 3. The API you build against
All of these need the officer token, except `/health`. The base address is configurable (default `http://127.0.0.1:8000`).

| Call | Returns |
|---|---|
| `GET /health` | `{"status": "ok"}`: is Sentinel running? |
| `GET /api/v1/mascot/state` | `{"state", "message", "session_id"}`: the latest session Sentinel decided, computed from real gateway events. `state` is one of the mascot's nine states; `message` is the sentence to show (may be empty). With no session it is `sleeping`. **Built for you today, with tests** |
| `GET /approvals` | `{"pending": [card, ...]}` |
| `GET /approvals/{approval_id}` | one card: `{"approval_id", "session_id", "tool", "args", "summary", "status", "expires_in"}` (seconds) |
| `POST /approvals/{approval_id}` with `{"decision": "approve"}` or `{"decision": "deny"}` | the updated card; 409 if it already expired or was resolved |
| WebSocket `/ws` (optional) | send `{"type": "auth", "token": "<token>"}` first, then receive every event as JSON. Polling the mascot state is simpler, so start with that |

**The mascot.** Use `design/mascot/sentinel-mascot.js` as it is: one file, no dependencies, no network.
- Copy it into the extension with a small script (`extension/scripts/copy-mascot`), so it stays identical to the one the site uses. Don't edit the copy; changes go to the original.
- Usage: `<sentinel-mascot state="denied" message="..." size="64" placement="above">`. Attributes are in `docs/contracts/MASCOT.md`.
- Another teammate is improving the animations in that same file, and you get those changes by re-copying it.

## 4. Design decisions (made, with the reasons)
- **Manifest V3, Chrome first, plain JavaScript.** No build step and no libraries, matching the rest of the project.
- **The mascot lives in an extension iframe, not in the page itself.**
  - The content script injects only a small fixed-position `<iframe src="chrome-extension://.../overlay.html">` inside a Shadow DOM host, bottom-left by default. The overlay page loads `sentinel-mascot.js` and talks to Sentinel.
  - **Why:**
    - Chrome content scripts can't register custom elements (in their isolated world `customElements` is null).
    - The page's CSS can't break an iframe.
    - The officer token never touches the page's JavaScript.
  - The iframe file must be listed in `web_accessible_resources`.
- **The token.** It is pasted once in the options page, by pasting the whole link `up` prints or the address plus the token.
  - Keep it in `chrome.storage.session`, which is cleared when the browser closes.
  - "Remember on this computer" may use `chrome.storage.local`, but only behind a checkbox with a warning: this token can approve actions.
  - The token is only ever used by extension pages (overlay, popup, options) and the service worker. It never goes into a content script, the page, a URL or the console log.
- **Updates come from polling.** The overlay polls `GET /api/v1/mascot/state` about every 700 ms while it is visible and stops when the tab is hidden. MV3 service workers sleep and `chrome.alarms` is too slow, so the overlay does the polling itself.
- **Permissions:**
  - **Content scripts:** only on `https://claude.ai/*` and `https://chatgpt.com/*`.
  - **Host permissions:** `http://127.0.0.1/*` and `http://localhost/*` for the API.
  - **Optional:** a tunnel address (`https://*.trycloudflare.com/*`), requested at run time only if the user sets one.
  - Nothing else: no `tabs`, no `<all_urls>`, no `scripting` unless E0 proves it is needed.
- **The mascot never shows a state Sentinel did not report.** It shows the state the API returns: `sleeping` with no session, `checking` while an action is being decided, and so on. When Sentinel is unreachable or the token is wrong, don't show a mascot state at all. Show a small grey "Sentinel not connected" pill instead.

## 5. Phases
Each phase is one pull request from a branch named `extension/e<n>-<short-name>`, using the repository's pull request template, with all code in `extension/`. You get three tries per phase. If a phase still fails after the third, stop and talk to Navdeep.

### E0 Spike (1 to 2 hours, by Fri 17:00)
- A minimal MV3 extension, loaded unpacked, that puts the overlay iframe with a static mascot on claude.ai and on chatgpt.com.
- From the overlay, it fetches `GET /health` from `http://127.0.0.1:8000`.
- **Record what works**, especially:
  - whether either site's Content Security Policy blocks the extension iframe;
  - whether Chrome's local-network protections ask for permission or block the call to 127.0.0.1.
- **If the iframe is blocked**, the fallback is Chrome's side panel (`chrome.sidePanel`), which needs no injection into the page at all.

Done when: Navdeep has seen it on both sites, and the notes on CSP and local-network behaviour are in the pull request.

### E1 Pairing and live state
- **Options page:** paste the link, or the address and token. A "Test connection" button checks `/health` and then `/api/v1/mascot/state`, and reports plainly ("connected", "Sentinel not running", "token rejected").
- **Overlay:** polls the state and shows the mascot and its message. When Sentinel can't be reached it shows the "not connected" pill. It can be minimised to a small dot and dragged, and remembers its position per site.
- **Popup (toolbar button):** shows connection status, a "show on this site" switch per site, and a link to open Sentinel's console.

Done when: the scripted poisoned quotation in Sentinel Chat (§2) makes the mascot on claude.ai go from `checking` to `denied` with "That would send restricted data out.", within about a second of the decision.

### E2 Approvals from the browser
- When the state is `needs-approval`, the overlay's bubble offers "Review".
- The popup (or a small card opened from the overlay) lists `GET /approvals`. Each card shows the tool, the summary, the exact arguments (readable and shortened, with the full text on expand), and the time left.
- **Approve** asks for confirmation first. **Deny** is one click. Both call `POST /approvals/{id}` and then show the result.
- An expired or already resolved approval (409) is explained, not hidden.

Done when: the "Update a vendor's bank details" task's held action can be approved and denied from the extension. The chat shows the same outcome, and the audit log in the console has the approval.

### E3 Polish
- **Follows the system theme;** the mascot's `theme` attribute is set to match.
- **Reduced motion is respected** automatically by the mascot.
- **The optional `speak` switch** (off by default) reads messages aloud.
- **Keyboard:** the popup and options are fully keyboard-usable, with visible focus.
- **No console errors** on either site.
- **Icons:** the mascot's face as the toolbar icon, drawn simply, not taken from any other brand.
- **README:** `extension/README.md` covers install (load unpacked), pairing, permissions and what the extension does not do.

### E4 Only with Navdeep's go-ahead: coverage hints (research)
The product's biggest open problem is that other connectors in the same chat (for example Gmail) bypass Sentinel. An extension could look at the page to warn "Gmail is also connected in this chat: Sentinel cannot see what Gmail does". That means reading the page, which is a privacy and honesty decision. **Do not start it without Navdeep.** If approved:
- write down exactly which page elements are read;
- read nothing else;
- send nothing anywhere;
- label it "hint", not "detection".

## 6. Rules
- No remote code, no analytics, no external requests other than the Sentinel address the user configured.
- It never claims to block or protect. The words are Sentinel's: ALLOWED, DENIED, NEEDS APPROVAL, QUARANTINED, and the message the API gave.
- No Anthropic or OpenAI branding or look-alike styling. It sits on their pages, so it must be clearly ours.
- Synthetic data only when testing; never real e-mail addresses or documents.
- No new libraries.

## 7. QA for every pull request
- [ ] Loads unpacked in Chrome with no errors on `chrome://extensions`.
- [ ] Works on claude.ai and chatgpt.com, signed in, in the dark and light themes.
- [ ] Network: the only requests the extension makes go to the configured Sentinel address. Check the service worker, popup and overlay in DevTools.
- [ ] The token appears in no content script, page variable, URL or log line. Search the page's DevTools for it.
- [ ] Sentinel stopped gives "not connected" (no mascot state); a wrong token gives "token rejected".
- [ ] The phase's own "done when" is met, with a short screen recording in the pull request.
- [ ] `extension/README.md` is updated for anything a user needs to know.

## 8. Who to ask
Navdeep decides scope and merges. Claude (with Navdeep) owns the backend. If you need an endpoint or a field that isn't listed in §3, ask; don't work around it in the extension.
