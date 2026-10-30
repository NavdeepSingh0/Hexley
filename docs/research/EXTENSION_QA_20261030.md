# Browser extension: review and live test, 30 Oct 2026

Branch `feat/extension` by Aadarsh Parmar (6 commits, 30 Oct 12:09 to 13:25), merged into `main` locally in `3557b27`. This is what was checked, how, and what is left. Everything below was run, not read: the extension was loaded unpacked into real Chromium 156 (Playwright's build; branded Chrome 137 and later ignores the load flag) against a live Sentinel with the F1 code, and driven over the DevTools protocol.

## What was checked and what happened
| Check | Result |
|---|---|
| The extension loads and its service worker starts (the manifest uses an SVG toolbar icon) | **Loads.** The options page opened on install, as the code intends |
| The overlay polls `GET /api/v1/mascot/state` with the token from session storage and drives the mascot | **Works.** After a real scripted denial it showed `denied` with Sentinel's own sentence ("That would send restricted data out."); after a held bank-details change it showed `needs-approval` |
| The popup | **Works.** "Connected" and the current state |
| The token | Only extension pages (overlay, popup, options) use it. The content script never touches it. It sits in session storage unless "Remember across browser restarts" is ticked, which warns "Stores the token on disk" |
| The content script on claude.ai | **Injects.** The host element is in the page and the overlay iframe target was created, on claude.ai's Cloudflare check page (not a signed-in page; see "not tested") |
| Review panel and approving from the browser | **Broken as merged, fixed in `main`.** See below |
| Hook-route decisions (F1) reaching the mascot | **Yes.** A held command reported through the hook route made `/api/v1/mascot/state` return `needs-approval` (`test_check.py`) |

## The blocking bug (fixed in main)
`overlay.js` looked for an approval card with `status === 'PENDING'`; Sentinel sends `"pending"`. The Review panel therefore opened **empty** (no tool, no arguments), and **Approve did nothing**: the approval stayed pending and the held call stayed held. With the one-word fix the panel shows the tool, the summary, the exact arguments and the countdown, two-step Approve resolves it, the chat continues and the mascot returns to idle. `test_the_approval_card_and_mascot_state_have_the_shape_the_extension_reads` pins the strings the extension depends on.

## Fixed afterwards (same day, on his branch, then merged)
Each was checked again in real Chromium on a page where the content script runs (`scripts/extension_qa.mjs`: **14 checks, all passed**).
1. **The Review panel is clipped.** The overlay now tells the page how tall it needs to be (`overlay.js` sends a `resize` message when its content changes) and the frame grows upward from 260 to 548 px while the panel is open, then shrinks back. The heading, tool, arguments, countdown and both buttons are inside the frame.
2. **Message listeners did not check who was talking.** `content.js` now accepts a size request only from the overlay frame itself and only inside bounds (48 to 420 wide, 48 to 640 tall); `overlay.js` accepts theme messages only from its parent. A message posted by the page itself is ignored (checked).
3. **Layout work on every DOM change.** The measurement now runs at most once per animation frame, however many changes arrive.
4. **The tunnel option is removed, not completed.** My first note said the options page had to ask for the permission and that Sentinel's cross-origin rules were in the way. That was wrong on both counts: an extension page with a host permission is not subject to those rules, and the real reason is simpler. Sentinel's tunnel points at the **AI gateway** only, so the officer API (which the extension talks to) is not reachable through it, and the officer token must not leave this computer. The options page now accepts only `http://127.0.0.1` or `http://localhost` and refuses any other address (checked: nothing is stored), the optional tunnel permission and its background handler are gone, and the README says so.
5. **The popup's per-site switches did nothing.** Found while reading the code: `popup.js` saved them, but `content.js` never read them. The overlay now follows the switch for its own site, live (off removes it at once, on puts it back once; checked).
6. **README.** It now says the extension is in `main`, installs with Load unpacked on the `extension/` folder, and lists the permissions without the tunnel.

## Not tested
- A **signed-in** claude.ai or chatgpt.com page: the sidebar-aware positioning depends on those sites' own layout, and their page security policy might block the overlay frame (it was allowed on the check page). **Navdeep should load it unpacked in his real Chrome and look.**
- Firefox, Edge, any other browser.
- A real long session, and CPU use while a reply streams.
- Keyboard use and a screen reader.

## What the extension is, and is not
It shows what Sentinel decided and lets the officer approve or deny from the browser. It enforces nothing, and it reads nothing from the page except where the sidebar edge is. The officer token it holds can approve actions, so it should be treated as a password.
