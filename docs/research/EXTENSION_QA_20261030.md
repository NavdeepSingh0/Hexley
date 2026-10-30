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

## For Aadarsh (not fixed here, to avoid conflicting with his work)
1. **The Review panel is clipped.** The overlay never asks the page to resize its iframe (`content.js` supports a `resize` message; `overlay.js` never sends one), so the panel is cut off at the top of its 260 by 260 box: the "NEEDS APPROVAL" heading is partly hidden. Send `{source: 'sentinel-overlay', type: 'resize', width, height}` when the panel opens and closes.
2. **Message listeners do not check who is talking.** `content.js` accepts `sentinel-overlay` messages from any window on the page, so a script on the page can resize the iframe; `overlay.js` accepts `sentinel-content` theme messages from any parent. Check `e.source === iframe.contentWindow` (content script) and `e.source === window.parent` (overlay).
3. **Layout work on every DOM change.** A `MutationObserver` on the whole document calls `getBoundingClientRect` on each mutation. Chat pages mutate constantly while a reply streams, so this can slow them down. Throttle it with `requestAnimationFrame`.
4. **A tunnel address cannot be used yet.** `background.js` can request the optional `trycloudflare.com` permission, but nothing in the options page asks for it, and Sentinel's API only allows the console's origin for cross-origin calls. Fine for `127.0.0.1`; not for a tunnel.
5. The README says to check out `feat/extension`; it is now in `main`. The install steps should say to open `chrome://extensions`, **Load unpacked**, and choose the `extension/` folder.

## Not tested
- A **signed-in** claude.ai or chatgpt.com page: the sidebar-aware positioning depends on those sites' own layout, and their page security policy might block the overlay frame (it was allowed on the check page). **Navdeep should load it unpacked in his real Chrome and look.**
- Firefox, Edge, any other browser.
- A real long session, and CPU use while a reply streams.
- Keyboard use and a screen reader.

## What the extension is, and is not
It shows what Sentinel decided and lets the officer approve or deny from the browser. It enforces nothing, and it reads nothing from the page except where the sidebar edge is. The officer token it holds can approve actions, so it should be treated as a password.
