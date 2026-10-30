# Deploying Sentinel (website, console, chat) on Render

30 Oct 2026. One container serves the website, the console, the chat, the officer API and the AI gateway, all on the one port the host exposes (D-055). The gateway demands a session token on every call. The connectors run inside the same container. Demo data is synthetic; connector data is whatever the test accounts hold, so use test accounts only.

## What you get, and what you do not
| You get | You do not get |
|---|---|
| A public address for the website, the console, the chat (scripted, replay and the live model), the docs and the AI gateway at `/mcp` | **Sending mail through the Gmail connector on the free plan.** Render's free plan blocks outbound SMTP (ports 25, 465, 587). The connector can read mail, and a send Sentinel refuses never reaches SMTP, but an allowed send fails there |
| The same program as on your laptop (`up --demo`): tamper and restore work, the audit log verifies | Storage that survives a restart: chats, sessions, sign-ins, tool pins and the audit log start fresh each time the service restarts, redeploys or wakes from sleep, so an AI client must sign in again |
| A cap on the hosted model: 300 requests in total (retries count) | A promise that the live model answers: it can be slow or rate-limited, as on a laptop |

Vercel cannot run this: Sentinel is a long-running Python server with WebSockets and in-memory state, which Vercel's serverless functions do not offer. Render, Fly.io, Google Cloud Run and Koyeb can all run the same `Dockerfile`.

## Steps (about 15 minutes, most of it Render building)
1. **Make a token.** In the repository folder run:
   `python -c "import secrets; print(secrets.token_urlsafe(24))"`
   Keep it. Anyone who has it can use the console and the chat, including the live model, so give it only to people you trust. It must be at least 24 characters of letters, digits, `-` and `_`; Sentinel refuses to start in the cloud with anything else.
2. **Render account.** Go to render.com and sign in with GitHub. When asked, let Render read the repository `NavdeepSingh0/Sentinel` (it is private).
3. **Create the service.** New, then **Blueprint**, choose the repository and the `main` branch. Render reads `render.yaml` and shows one web service called `sentinel` on the free plan in Singapore.
4. **Fill in the secrets** it asks for:
   - `SENTINEL_API_TOKEN`: the token from step 1.
   - `NVIDIA_API_KEY`: your key from build.nvidia.com. Paste it into Render only. Never into chat or git.
   - `GITHUB_TOKEN`, `NOTION_TOKEN`, `SLACK_USER_TOKEN`, `GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`: test accounts only. A connector whose value is empty is not started, and the log says so.
5. **Apply.** The first build takes several minutes (it builds the website, then the Python image). Watch the Logs tab. When it says `Hexley up`, it is running.
6. **Open it.** The address is `https://sentinel-xxxx.onrender.com` (Render shows it at the top of the page). Add the token to open the console and chat:
   `https://sentinel-xxxx.onrender.com/#token=<your token>`
   The page moves the token out of the address bar as soon as it opens. The public pages need no token.

## Your own domain
`render.yaml` sets `SENTINEL_PUBLIC_URL=https://hexley.site`, which turns on sign-in for AI clients, so the connector address is `https://hexley.site/mcp`. In Render, add the domain under Settings, then Custom Domains, and create the DNS records Render shows at your registrar. Until the domain answers, a client's sign-in will not work: set `SENTINEL_PUBLIC_URL` to the `onrender.com` address instead. Not yet done or tested.

## Check it works
- `https://<address>/health` shows `{"status":"ok"}`.
- The home page loads; the docs load.
- With the token link: the console's three-lane demo runs; Sentinel Chat in **Scripted attacker** mode shows the denial; **Live model** answers (slowly at first).
- The log does not contain your token (Sentinel never prints it on a hosting platform).
- The log says `Connectors ready in ...` and lists any connector not started.
- **Signing in an AI client:** the officer code is printed in Render's Logs tab; the console does not show it yet. Only people on your Render account can read those logs.

## Things to know before you present
- **The free plan sleeps** after about 15 minutes without a visit. Waking is a full restart: measured under a hard limit of 0.1 CPU (below), about 2 to 3 minutes before it answers, and every sign-in and session is gone. Open the link and sign the AI client in about ten minutes before you start, and keep the page open. Paid plans do not sleep.
- **The free plan is small** (512 MB of memory, a fraction of a CPU). It is enough for the demo; live-model chats and the first page load will feel slower than on your laptop.
- **A restart clears everything**, including the 300-request model cap. If the cap is reached the chat says so and scripted and replay modes still work.
- **To change the token or a key:** change it under Environment in Render and redeploy. **To stop it:** Suspend the service.
- `autoDeploy` is off on purpose: pushing to GitHub does not change the live demo until you press Manual Deploy.

## What was and was not checked
**Measured on 30 Oct 2026, n=1, on this laptop under Docker with `-m 512m --cpus 0.1`, dummy connector values and no real account. That only imitates Render's free plan:** the image builds (635 MB before the last change, not re-measured); the service answers after 139 s; connectors ready 37.5 s later; memory 279 MiB of 512; first tool list by a client 2.6 s; an off-slip send refused; a connector with a bad token skipped without stopping the others; no connector value in the log.

Before the last change the npx wrappers used 271 MB, memory reached about 500 MiB of 512, and the first listing took 65 s at 0.5 CPU, so the connectors now run without npx. A longer test found that `up` gave up on its tool server after 25 s at 0.1 CPU; the wait is now 180 s.

**Not checked:** Render itself has not run this image; a real connector token in the container; memory under real traffic or a large mail or page (279 MiB is an idle figure); the Slack connector, which is disabled; the domain.
