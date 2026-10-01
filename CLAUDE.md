# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An MCP (stdio) server exposing the Yandex Wiki REST API (`https://api.wiki.yandex.net/v1`) as tools. Published to PyPI as `yandex-wiki-mcp-server`, normally run via `uvx`.

## Commands

```bash
uv sync                                   # dev environment from uv.lock (mcp 1.x pinned)
uv run python -m unittest -v              # tests, no network: requests go through httpx.MockTransport

export WIKI_OAUTH_TOKEN=<y0_-token>       # or IAM: export WIKI_IAM_TOKEN=$(yc iam create-token)
export WIKI_CLOUD_ORG_ID=<org-id>
uv run python -m yandex_wiki_mcp          # run the server on stdio
```

CI (`.github/workflows/tests.yml`) runs the unit tests on Python 3.10 and 3.12 for every push and pull request. Version lives only in `pyproject.toml`.

This fork is installed from git (`uvx --from git+https://github.com/ssubbotin/yandex-wiki-mcp@master yandex-wiki-mcp-server`). The PyPI name `yandex-wiki-mcp-server` belongs to the upstream project and ships none of the fork's changes; do not publish under it.

`mcp` is pinned below 2: in 2.x the low-level `Server` lost the `@list_tools()` / `@call_tool()` decorators (handlers move into the constructor), and the server crashes at import. Moving to 2.x means rewriting `server.py` only.

Auth env vars are read at request time, not at startup: a replaced token is picked up by the next tool call, but only from the process's own environment. Order: `WIKI_OAUTH_TOKEN` → `TRACKER_OAUTH_TOKEN` → `TRACKER_TOKEN` (the name yandex-tracker-mcp uses) with scheme `OAuth`, then `WIKI_IAM_TOKEN` → `TRACKER_IAM_TOKEN` with scheme `Bearer`; `WIKI_CLOUD_ORG_ID` → `TRACKER_CLOUD_ORG_ID` for `X-Cloud-Org-Id`.

## Architecture

Three layers, one file each under `src/yandex_wiki_mcp/`:

- `client.py` — plain synchronous `httpx` functions, one per API endpoint. No state, no shared client: `_client()` builds a fresh `httpx.Client` per call so headers pick up the current env vars.
- `server.py` — MCP surface. `list_tools()` returns hand-written `Tool` definitions with inline JSON schemas; `call_tool()` is a single `match` dispatching to `client`. Every result is JSON-dumped through `_ok()`; every exception is caught and returned as `Error: ...` text through `_err()` so the client sees a message instead of a protocol failure. HTTP errors go through `client._check()`, which raises `WikiApiError` with the API's `error_code`, `debug_message` and `details`; use it instead of `raise_for_status()` in new client functions.
- `__main__.py` — `asyncio.run(run())`.

Adding a tool means editing three places in lockstep: a `client.py` function, a `Tool` entry in `list_tools()`, and a `case` in `call_tool()`. Nothing generates one from another. Add a test in `tests/test_client.py` and a row in the README tool table.

## API quirks worth knowing

- **Slugs must not be percent-encoded.** Slugs are paths like `scp/docs/my-page`, and the API rejects encoded slashes. `_get_with_slug()` therefore builds the query string by hand and passes a full URL to `httpx`, bypassing its param encoding. Do not "fix" this into `params={"slug": ...}`.
- **Updates use POST, not PUT** — `POST /v1/pages/{id}` for edits, `POST /v1/pages/{id}/append-content` for appends.
- **`get_page(slug)` costs two requests.** `GET /v1/pages?slug=` returns metadata without content; the function then re-fetches by ID with `fields=content,breadcrumbs,attributes` and merges. Content fields only ever come from the by-ID endpoint.
- Descendants endpoints paginate by opaque `cursor`, not page number.
- **Dynamic tables are not part of page content.** A page holds only `{% wgrid id="UUID" %}` markers; rows live behind `GET /v1/grids/{uuid}` (filters `only_cols`, `only_rows`, `filter`, `sort`, `revision`). `get_page`/`get_page_by_id` expand each marker into a Markdown table below it (`expand_grids=False` keeps raw content); writes go through `POST /v1/grids/{uuid}/cells` (`{"cells": [{"row_id", "column_slug", "value"}]}`) and `POST /v1/grids/{uuid}/rows`.
- **Legacy table pages (`page_type == "grid"`) are unreadable through the public API**: content comes back `null`, `/v1/pages/{id}/grids` is empty and `/v1/grids/{page id}` is 404. `get_page_by_id` raises `LegacyGridPageError` instead of returning an empty page.
- **Search** is `POST /v1/search` with `{"query", "limit" (1..50), "cursor" (page number 1..500), "filters": {"type": "page"|"file"}}`; results carry `slug`, `title`, `url`, a content snippet and `modified_at`.
- **History** is `GET /v1/pages/{id}/revisions` (`page_size`, opaque `cursor`); an old version is read with `GET /v1/pages/{id}?revision_id=…`.
