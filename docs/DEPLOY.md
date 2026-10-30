# Deploying Hexley (website, console, chat, gateway)

31 Oct 2026. The deployment is at **https://hexley.site**, on an AWS EC2 t3.micro running Ubuntu 24.04 in Sydney (the free plan refused other regions). One container serves the website, the console, the chat, the officer API and the AI gateway on one port (D-055), with Caddy in front for HTTPS, compression and cache headers. The gateway demands a session token on every call. The connectors stay in the AI apps, and Hexley holds none of their credentials. Demo data is synthetic. Use test accounts only.

## What you get, and what you do not
| You get | You do not get |
|---|---|
| The website, console, chat (scripted, replay and the live model), docs and the gateway at `/mcp` on one public address | Storage that survives a restart: chats, sessions, sign-ins, tool pins, the audit log and its signing key start fresh on every restart or deploy, so an AI client must reconnect with one click and a hook's token must be issued again |
| Connecting with Google: any Google account, then one Allow page. The slip lasts 7 days | Separate slips per person: everyone who signs in shares one slip and one list of destinations |
| A limit per address: 30 sign-in and 300 gateway requests a minute (D-061), and a cap of 300 model requests in total | Protection against many addresses, or a promise that the live model answers: it can be slow or rate-limited |

## Deploying a change
From the `sentinel` folder, in PowerShell, with the SSH key at `%USERPROFILE%\.ssh\hexley.pem`:

```
& scripts\deploy\deploy_image.ps1 -Server ubuntu@<address> -Domain hexley.site -Work <a scratch folder>
```

It builds the image here, because the server is too small to build it, copies it across and restarts. **Every deploy signs everyone out and clears the log.** Do not deploy just before a demo.

## A new server, from nothing
1. Launch Ubuntu 24.04 on a t3.micro (this one has a 15 GB disk, about a third used). Open ports 22, 80 and 443. Attach an Elastic IP so the address survives a stop.
2. Point the domain's `A` record at that address.
3. Run the deploy command above. `scripts/deploy/ec2_setup.sh` installs Docker, adds swap and generates the officer token into the root-only file `/etc/hexley/hexley.env`.
4. Create a Google OAuth client of the Web application type, with the redirect address `https://<domain>/oauth/google/callback`, and publish the app. Put its values on the server with `scripts/deploy/set_google.sh`, which asks for them on the server. Never paste them into chat or git.
5. Put the model keys on the server with `scripts/deploy/set_model_keys.sh`, in the same way.
6. Set `SENTINEL_OAUTH_DESTINATIONS` and `SENTINEL_OAUTH_INTERNAL` in that file to the test addresses, channels and pages the slip may reach.

## Check it works
- `https://<address>/health` shows `{"status":"ok"}`.
- The home page and docs load.
- With the officer's link (`https://<address>/#token=<token>`, whose token the page moves out of the address bar): the console's demo runs, and the chat in **Scripted attacker** mode shows the denial.
- Connecting from Claude.ai goes to Google's account picker, then Allow, then back.
- The log does not contain the token or a key.

## Things to know before you present
- **A deploy or restart signs everyone out.** Reconnect Claude.ai with one click, and issue the Antigravity hook's token again.
- **The server is small** (1 GB of memory, with swap). The live model can take about 35 s for a chat.
- **The SSH rule is open to any address** because the presenter's address changes. The key is still required. Tighten it after the event.
- **AWS identity verification failed** because the account name does not match; the server launched anyway. If AWS stops it, `render.yaml` and the same `Dockerfile` are the backup. **The backup has never run on Render itself**, and Render's free plan sleeps and blocks SMTP.

## What was and was not checked
**On the live server, n=1 per test:** Google sign-in from Claude.ai; `hexley_setup` and the preferences route; the hook route with Gmail, Slack and Notion; the Antigravity hook with GitHub; one live-model chat; a held call approved in the console and used once (`docs/PHASE_LOG.md`, rows G1 to G5 and F3c).

**Not checked:** a second person's sign-in; signing in on a phone; memory under real traffic; several people connected at once; the Render backup.
