# Sentinel

**The AI can only do the job you gave it.**

Sentinel is an MCP gateway that sits between an AI agent and its tools. It checks every action against the task the officer approved, where the data came from, and where it is going, and blocks what the task never asked for. No LLM makes any security decision.

Team 404 Disruptors · Zinnovatio 4.0

## Status
Pre-build. Docs and M0 spikes only; no feature code yet. The table of what is real, partial and roadmap will be kept honest here as work lands.

## Docs
- [docs/MVP.md](docs/MVP.md): what we build and present (source of truth)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md): layout, interfaces, build order
- [docs/ADVERSARIAL_TESTS.md](docs/ADVERSARIAL_TESTS.md): attack matrix that becomes test oracles
- [docs/spikes/M0-results.md](docs/spikes/M0-results.md): measured spike results

## Setup
```
python -m pip install --user uv
python -m uv sync
python -m uv run pytest
```

All demo data is synthetic. Domains use `.example`.
