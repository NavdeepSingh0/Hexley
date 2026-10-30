"""The website, console, API and gateway on one port, for a host that exposes only one (plan F2, D-055).

The gateway's own routes (`/mcp`, and with sign-in on `/authorize`, `/token`, `/register`, `/.well-known/...`,
`/oauth/...`) go to the gateway; everything else goes to the API app, whose last route is the website's catch-all, so
the order matters: a sign-in path must never fall through to the site. Nothing changes about who may do what: the gateway
still demands a session token on every call and the API still demands the officer's token.

Because any Google account may be allowed to sign in, a public deployment also limits requests per address (D-061). It is a
brake on one noisy address, not protection against many.
"""

from __future__ import annotations

import ipaddress
import time

# Requests per minute from one address. Starting a sign-in is rare for a person, and each one costs the server memory.
SIGN_IN_LIMIT = 30
GATEWAY_LIMIT = 300
_SIGN_IN = ("/register", "/authorize", "/token", "/oauth/")
_MAX_ADDRESSES = 5000
# Inside a container the proxy on the same computer arrives from Docker's bridge, not loopback: found on the live server, where every
# visitor counted as one address. The port is published on loopback only, so nothing else can arrive from these.
_PROXY_NETS = tuple(ipaddress.ip_network(n) for n in ("127.0.0.0/8", "::1/128", "172.16.0.0/12"))


class RateLimit:
    """A count per address per minute. Small enough to read, and it forgets everything each minute."""

    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.minute = -1
        self.counts: dict[tuple[str, str], int] = {}

    def allow(self, address: str, kind: str, limit: int) -> bool:
        minute = int(self.clock() // 60)
        if minute != self.minute or len(self.counts) > _MAX_ADDRESSES:
            self.minute, self.counts = minute, {}
        key = (address, kind)
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key] <= limit


def _from_the_proxy(peer: str) -> bool:
    try:
        address = ipaddress.ip_address(peer)
    except ValueError:
        return False
    return any(address in net for net in _PROXY_NETS if address.version == net.version)


def client_address(scope) -> str:
    """Who is asking. Behind the proxy on this computer, the last X-Forwarded-For entry is the one the proxy itself added; the earlier
    ones are whatever the caller claimed, so they are ignored."""
    peer = (scope.get("client") or ("unknown", 0))[0]
    if not _from_the_proxy(peer):
        return peer
    for name, value in scope.get("headers") or []:
        if name == b"x-forwarded-for":
            return value.decode("latin-1").rsplit(",", 1)[-1].strip() or peer
    return peer


class OnePort:
    def __init__(self, api, gateway, limit: RateLimit | None = None):
        self.api, self.gateway = api, gateway
        self.limit = limit or RateLimit()
        self.paths = tuple(sorted({r.path for r in gateway.routes if getattr(r, "path", None)}))

    def is_gateway(self, path: str) -> bool:
        return any(path == p or path.startswith(p + "/") for p in self.paths)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self.gateway(scope, receive, send)  # the gateway's session manager needs it; the API app has none of its own
            return
        path = scope.get("path", "")
        if scope["type"] == "http" and self.is_gateway(path):
            sign_in = path.startswith(_SIGN_IN)
            kind, allowed = ("sign-in", SIGN_IN_LIMIT) if sign_in else ("gateway", GATEWAY_LIMIT)
            if not self.limit.allow(client_address(scope), kind, allowed):
                await send({"type": "http.response.start", "status": 429,
                            "headers": [(b"content-type", b"text/plain; charset=utf-8"), (b"retry-after", b"60")]})
                await send({"type": "http.response.body", "body": b"Too many requests from this address. Try again in a minute."})
                return
            await self.gateway(scope, receive, send)
        else:
            await self.api(scope, receive, send)
