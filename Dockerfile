# Sentinel for a hosting platform (plan D1; docs/DEPLOY.md). Two stages: build the website and the console, then a small Python image
# that serves them with the API, the chat and the gateway. Everything is synthetic demo data; no secret is baked into the image
# (the officer token and the model keys come from the platform's environment).

FROM node:22-slim AS web
WORKDIR /app
COPY site/package.json site/package-lock.json site/
COPY console/package.json console/package-lock.json console/
RUN npm --prefix site ci && npm --prefix console ci
COPY design design
COPY site site
COPY console console
RUN npm --prefix site run build && npm --prefix console run build

FROM python:3.13-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 UV_LINK_MODE=copy
RUN pip install uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src src
RUN uv sync --frozen --no-dev
COPY recordings recordings
COPY --from=web /app/site/dist site/dist
COPY --from=web /app/console/dist console/dist
# Node runs the connectors that are npm packages (Notion, mail). Taken from the build stage, so it is the same version.
COPY --from=web /usr/local/bin/node /usr/local/bin/node
COPY --from=web /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s ../lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm && ln -s ../lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx
# The pinned connector versions in upstreams.yaml (a test holds the two together), installed with their install scripts off and run
# directly, without npx, which measured more memory than the servers themselves. The directory belongs to root: read-only at run time.
RUN npm install --prefix /app/connectors --omit=dev --ignore-scripts --no-audit --no-fund @notionhq/notion-mcp-server@2.6.1 mcp-mail-server@2.1.2
ENV SENTINEL_CONNECTORS_DIR=/app/connectors
RUN useradd --create-home sentinel && mkdir -p /tmp/sentinel && chown -R sentinel /tmp/sentinel
USER sentinel

# The officer API listens on every address (the platform's proxy needs that) and on the port the platform gives in $PORT. It refuses
# to start unless SENTINEL_API_TOKEN is a token you chose. The gateway shares that port (the host exposes only one, D-055) and still
# demands a session token on every call. The tool server stays on 127.0.0.1 inside the container. A visitor with no token may try the
# synthetic demo and chat, and nothing else (D-062).
ENV SENTINEL_HOST=0.0.0.0 SENTINEL_QUIET_LINKS=1 SENTINEL_ONE_PORT=1 SENTINEL_PUBLIC_DEMO=1
EXPOSE 10000
CMD [".venv/bin/python", "-m", "sentinel", "up", "--demo", "--no-browser", "--data-dir", "/tmp/sentinel"]
