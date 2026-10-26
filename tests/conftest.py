"""Shared fixtures: a full in-process Sentinel stack on ephemeral ports (tools, gateway, API)."""

import pytest_asyncio

from sentinel.stack import Stack, free_port, running_stack, serve  # noqa: F401  (re-exported for spikes and tests)

API_TOKEN = "test-api-token"
DOWNSTREAM_TOKEN = "test-downstream-secret"


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def stack():
    async with running_stack(API_TOKEN, DOWNSTREAM_TOKEN) as s:
        yield s
