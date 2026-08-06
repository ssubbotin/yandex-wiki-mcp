# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An MCP (stdio) server exposing the Yandex Wiki REST API (`https://api.wiki.yandex.net/v1`) as tools. Published to PyPI as `yandex-wiki-mcp-server`, normally run via `uvx`.

## Commands

```bash
uv venv && uv pip install -e .          # local install

export WIKI_IAM_TOKEN=$(yc iam create-token)
export WIKI_CLOUD_ORG_ID=<org-id>
python -m yandex_wiki_mcp               # run the server on stdio
```

There is no test suite, linter config, or CI in the repo. Version lives only in `pyproject.toml`; a release is a version bump plus `uv build && uv publish`.

Auth env vars are read at request time (not at startup), so a stale IAM token can be replaced without restarting nothing else — but the running process caches nothing, so it picks up only what was in its own environment. `WIKI_*` wins over the `TRACKER_*` fallback names.

## Architecture

Three layers, one file each under `src/yandex_wiki_mcp/`:

- `client.py` — plain synchronous `httpx` functions, one per API endpoint. No state, no shared client: `_client()` builds a fresh `httpx.Client` per call so headers pick up the current env vars.
- `server.py` — MCP surface. `list_tools()` returns hand-written `Tool` definitions with inline JSON schemas; `call_tool()` is a single `match` dispatching to `client`. Every result is JSON-dumped through `_ok()`; every exception is caught and returned as `Error: ...` text through `_err()` so the client sees a message instead of a protocol failure.
- `__main__.py` — `asyncio.run(run())`.

Adding a tool means editing three places in lockstep: a `client.py` function, a `Tool` entry in `list_tools()`, and a `case` in `call_tool()`. Nothing generates one from another.

## API quirks worth knowing

- **Slugs must not be percent-encoded.** Slugs are paths like `scp/docs/my-page`, and the API rejects encoded slashes. `_get_with_slug()` therefore builds the query string by hand and passes a full URL to `httpx`, bypassing its param encoding. Do not "fix" this into `params={"slug": ...}`.
- **Updates use POST, not PUT** — `POST /v1/pages/{id}` for edits, `POST /v1/pages/{id}/append-content` for appends.
- **`get_page(slug)` costs two requests.** `GET /v1/pages?slug=` returns metadata without content; the function then re-fetches by ID with `fields=content,breadcrumbs,attributes` and merges. Content fields only ever come from the by-ID endpoint.
- Descendants endpoints paginate by opaque `cursor`, not page number.
