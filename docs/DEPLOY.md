# Deploying Sentinel (website, console, chat) on Render

30 Oct 2026. One container serves the website, the console, the chat and the officer API. The AI gateway runs inside the same container and is **not** reachable from outside. All data is synthetic.

## What you get, and what you do not
| You get | You do not get |
|---|---|
| A public address for the website, the console, the chat (scripted, replay and the live model) and the docs | The Claude.ai connector. Claude.ai needs the gateway reachable from the internet; keep using `python -m sentinel up --tunnel` on your laptop for that |
| The same program as on your laptop (`up --demo`): tamper and restore work, the audit log verifies | Storage that survives a restart: chats, sessions and the audit log start fresh each time the service restarts or redeploys |
| A cap on the hosted model: 300 requests in total (retries count) | A promise that the live model answers: it can be slow or rate-limited, as on a laptop |

Vercel cannot run this: Sentinel is a long-running Python server with WebSockets and in-memory state, which Vercel's serverless functions do not offer. Render, Fly.io, Google Cloud Run and Koyeb can all run the same `Dockerfile`.

## Steps (about 15 minutes, most of it Render building)
1. **Make a token.** In the repository folder run:
   `python -c "import secrets; print(secrets.token_urlsafe(24))"`
   Keep it. Anyone who has it can use the console and the chat, including the live model, so give it only to people you trust. It must be at least 24 characters of letters, digits, `-` and `_`; Sentinel refuses to start in the cloud with anything else.
2. **Render account.** Go to render.com and sign in with GitHub. When asked, let Render read the repository `NavdeepSingh0/Sentinel` (it is private).
3. **Create the service.** New, then **Blueprint**, choose the repository and the `main` branch. Render reads `render.yaml` and shows one web service called `sentinel` on the free plan in Singapore.
4. **Fill in the two secrets** it asks for:
   - `SENTINEL_API_TOKEN`: the token from step 1.
   - `NVIDIA_API_KEY`: your key from build.nvidia.com. Paste it into Render only. Never into chat or git.
5. **Apply.** The first build takes several minutes (it builds the website, then the Python image). Watch the Logs tab. When it says `Sentinel up`, it is running.
6. **Open it.** The address is `https://sentinel-xxxx.onrender.com` (Render shows it at the top of the page). Add the token to open the console and chat:
   `https://sentinel-xxxx.onrender.com/#token=<your token>`
   The page moves the token out of the address bar as soon as it opens. The public pages need no token.

## Check it works
- `https://<address>/health` shows `{"status":"ok"}`.
- The home page loads; the docs load.
- With the token link: the console's three-lane demo runs; Sentinel Chat in **Scripted attacker** mode shows the denial; **Live model** answers (slowly at first).
- The log does not contain your token (Sentinel never prints it on a hosting platform).

## Things to know before you present
- **The free plan sleeps** after about 15 minutes without a visit, and the first request afterwards takes up to a minute. Open the link two minutes before you start. Paid plans do not sleep.
- **The free plan is small** (512 MB of memory, a fraction of a CPU). It is enough for the demo; live-model chats and the first page load will feel slower than on your laptop.
- **A restart clears everything**, including the 300-request model cap. If the cap is reached the chat says so and scripted and replay modes still work.
- **To change the token or a key:** change it under Environment in Render and redeploy. **To stop it:** Suspend the service.
- `autoDeploy` is off on purpose: pushing to GitHub does not change the live demo until you press Manual Deploy.

## What was and was not checked
Checked on this computer: the program refuses to listen beyond this computer unless the token is yours and strong; it takes its port from `$PORT`; with those settings the API answers on every address, the gateway and the tool server answer on none but 127.0.0.1, and the token is not in the log; the model cap stops requests before they are sent (all tested, each with a deliberate-break check).

**Not checked:** the Docker image was never built to the end here (the first attempt stopped at a network error inside Docker, and the rebuild was skipped to deploy sooner), and Render itself has not run it. The first build on Render is therefore the first real test. If it fails, the build log names the step; the usual suspects are a file the image does not copy (see `.dockerignore`) and the free plan running out of memory during the website build.

## The website on Vercel (optional, in front of the Render service)
Why: the free Render service sleeps, so the first visit to its address can take up to a minute. Vercel serves the public pages from its own network, always awake, and only the chat's API calls reach Render (and wake it).

`site/vercel.json` does three things: it serves the built website; it passes `/api/...`, `/audit/...`, `/approvals/...` and `/health` through to the Render service (so the browser still talks to one address); and it sends `/console/...` to the Render service, because the console needs a WebSocket, which Vercel cannot pass through. The Render address is written in that file (`hexley.onrender.com`); change it there if the service is renamed.

Steps: in Vercel, Add New, Project, import the repository, set **Root Directory** to `site` (the framework shows as Vite), and deploy. Under Settings, General, make sure **Include source files outside of the Root Directory in the Build Step** is on: the website imports the mascot from the `design` folder.

Then open `https://<project>.vercel.app/#token=<your token>`. The token is stored by that address, separately from the Render address, so sign in once on each.

**Not checked:** this configuration has not run on Vercel. Two things to watch: a request that arrives while Render is asleep may time out once (reload and it works), and the console opens on the Render address, not the Vercel one.
