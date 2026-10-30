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
RUN useradd --create-home sentinel && mkdir -p /tmp/sentinel && chown -R sentinel /tmp/sentinel
USER sentinel

# The officer API listens on every address (the platform's proxy needs that) and on the port the platform gives in $PORT. It refuses
# to start unless SENTINEL_API_TOKEN is a token you chose. The gateway and the tool server stay on 127.0.0.1 inside the container.
ENV SENTINEL_HOST=0.0.0.0 SENTINEL_QUIET_LINKS=1
EXPOSE 10000
CMD [".venv/bin/python", "-m", "sentinel", "up", "--demo", "--no-browser", "--data-dir", "/tmp/sentinel"]
