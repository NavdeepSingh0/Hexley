"""The website, console, API and gateway on one port, for a host that exposes only one (plan F2, D-055).

The gateway's own routes (`/mcp`, and with sign-in on `/authorize`, `/token`, `/register`, `/.well-known/...`,
`/oauth/consent`) go to the gateway; everything else goes to the API app, whose last route is the website's catch-all, so
the order matters: a sign-in path must never fall through to the site. Nothing changes about who may do what: the gateway
still demands a session token on every call and the API still demands the officer's token.
"""

from __future__ import annotations


class OnePort:
    def __init__(self, api, gateway):
        self.api, self.gateway = api, gateway
        self.paths = tuple(sorted({r.path for r in gateway.routes if getattr(r, "path", None)}))

    def is_gateway(self, path: str) -> bool:
        return any(path == p or path.startswith(p + "/") for p in self.paths)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "lifespan":
            await self.gateway(scope, receive, send)  # the gateway's session manager needs it; the API app has none of its own
        elif scope["type"] == "http" and self.is_gateway(scope.get("path", "")):
            await self.gateway(scope, receive, send)
        else:
            await self.api(scope, receive, send)
