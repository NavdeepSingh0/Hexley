"""The built website is served at / by the API app (core plan F6): single-page-app fallback for site routes, API paths
untouched, FastAPI's own /docs switched off, a missing build a clear 404."""

import httpx
import pytest_asyncio
from fastapi import FastAPI
from fastapi.routing import APIRoute, APIWebSocketRoute

from sentinel.api import API_PREFIXES, create_api, mount_site

from .conftest import API_TOKEN


@pytest_asyncio.fixture
async def site(stack, tmp_path):
    dist = tmp_path / "site-dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html><title>Sentinel site</title><div id=root></div></html>", encoding="utf-8")
    (dist / "assets" / "app.js").write_text("console.log('app')", encoding="utf-8")
    (dist / "evidence.json").write_text('[{"n": 1}]', encoding="utf-8")
    console = tmp_path / "console-dist"
    console.mkdir()
    (console / "index.html").write_text("<html><title>Sentinel console</title></html>", encoding="utf-8")
    app = create_api(stack.rt, console_dir=console, site_dir=dist)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def test_the_home_page_and_real_files_are_served(site):
    r = await site.get("/")
    assert r.status_code == 200 and "Sentinel site" in r.text
    assert (await site.get("/assets/app.js")).text == "console.log('app')"
    assert (await site.get("/evidence.json")).json() == [{"n": 1}]


async def test_site_routes_fall_back_to_the_page_so_a_reload_or_a_shared_link_works(site):
    for path in ("/docs", "/docs/", "/how-it-works", "/integrations", "/connect", "/chat", "/pricing"):
        r = await site.get(path)
        assert r.status_code == 200 and "Sentinel site" in r.text, path


async def test_fastapis_own_docs_are_off_so_docs_is_the_websites_page(site):
    assert "Swagger" not in (await site.get("/docs")).text
    for path in ("/openapi.json", "/redoc"):
        r = await site.get(path)
        # /openapi.json looks like a file, so it is a 404; /redoc is a site route and gets the page, never ReDoc
        assert r.status_code == 404 or "Sentinel site" in r.text, path
        assert "openapi" not in r.text.lower()


async def test_a_missing_file_is_a_404_not_the_page(site):
    assert (await site.get("/assets/nope.js")).status_code == 404
    assert (await site.get("/favicon.ico")).status_code == 404


async def test_a_mistyped_api_path_is_a_404_never_html(site):
    for path in ("/api/v1/nope", "/api/v1/connect/extra", "/runs/", "/approvals/x/y", "/sessions/x/y", "/health/x", "/oauth/nothing"):
        r = await site.get(path)
        assert r.status_code in (404, 405) and "Sentinel site" not in r.text, path


async def test_api_routes_and_the_console_are_unchanged(site):
    assert (await site.get("/health")).status_code == 200
    assert (await site.get("/api/v1/connect")).status_code == 200
    assert (await site.get("/scenarios")).status_code == 401  # still behind the token
    r = await site.get("/console/")
    assert r.status_code == 200 and "Sentinel console" in r.text
    assert (await site.get("/scenarios", headers={"Authorization": f"Bearer {API_TOKEN}"})).status_code == 200


async def test_only_get_is_answered_for_the_site(site):
    assert (await site.post("/how-it-works")).status_code in (404, 405)
    assert (await site.put("/")).status_code in (404, 405)


async def test_a_path_cannot_climb_out_of_the_build_folder(site):
    for path in ("/../../pyproject.toml", "/%2e%2e/%2e%2e/pyproject.toml", "/assets/../../../pyproject.toml"):
        r = await site.get(path)
        assert "[project]" not in r.text, path


async def test_a_missing_build_says_how_to_build_it(tmp_path):
    app = FastAPI()
    mount_site(app, tmp_path / "nothing-here")
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/")
        assert r.status_code == 404 and "npm --prefix site run build" in r.text
        assert (await c.get("/how-it-works")).status_code == 404


def test_every_api_route_has_its_prefix_listed(stack, tmp_path):
    """A route added later under a new top-level path must be added to API_PREFIXES, or a mistyped call to it would be
    answered with the website."""
    app = create_api(stack.rt, console_dir=tmp_path, site_dir=tmp_path)
    paths = [r.path for r in app.routes if isinstance(r, (APIRoute, APIWebSocketRoute))]
    assert paths, "no routes found"
    missing = [p for p in paths if not p.startswith(API_PREFIXES)]
    assert not missing, f"add these to API_PREFIXES: {missing}"
