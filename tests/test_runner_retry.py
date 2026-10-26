"""The model client retries a turn that never happened (timeouts, dropped connections, 429/5xx) and says why when it gives up."""

import httpx
import pytest

from sentinel.agent import runner

OK = {"choices": [{"message": {"role": "assistant", "content": "done"}}]}


@pytest.fixture(autouse=True)
def no_backoff(monkeypatch):
    monkeypatch.setattr(runner, "RETRY_BASE_S", 0.0)


def endpoint():
    return runner.ModelEndpoint(provider="ollama", model="test-model")


async def call(handler):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        return await endpoint().chat(client, [{"role": "user", "content": "hi"}], [])


async def test_a_read_timeout_is_retried():
    seen = []

    def handler(request):
        seen.append(request)
        if len(seen) < 3:
            raise httpx.ReadTimeout("slow", request=request)
        return httpx.Response(200, json=OK)

    assert (await call(handler))["content"] == "done" and len(seen) == 3


async def test_5xx_and_429_are_retried():
    codes = iter([429, 500, 503])

    def handler(request):
        code = next(codes, 200)
        return httpx.Response(code, json=OK if code == 200 else {})

    assert (await call(handler))["content"] == "done"


async def test_giving_up_names_the_last_failure():
    def handler(request):
        raise httpx.ConnectError("refused", request=request)

    with pytest.raises(RuntimeError, match=r"6 times.*ConnectError"):
        await call(handler)


async def test_a_client_error_is_not_retried():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(401, json={"error": "bad key"})

    with pytest.raises(httpx.HTTPStatusError):
        await call(handler)
    assert len(seen) == 1
