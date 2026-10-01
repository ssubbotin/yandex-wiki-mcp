"""Yandex Wiki API client."""

import os
import re
import httpx
from typing import Any


BASE_URL = "https://api.wiki.yandex.net/v1"


def _get_headers() -> dict[str, str]:
    iam_token = (
        os.environ.get("WIKI_IAM_TOKEN")
        or os.environ.get("TRACKER_IAM_TOKEN")
    )
    org_id = (
        os.environ.get("WIKI_CLOUD_ORG_ID")
        or os.environ.get("TRACKER_CLOUD_ORG_ID")
    )
    if not iam_token:
        raise RuntimeError(
            "Set WIKI_IAM_TOKEN (or TRACKER_IAM_TOKEN) environment variable"
        )
    headers = {"Authorization": f"Bearer {iam_token}"}
    if org_id:
        headers["X-Cloud-Org-Id"] = org_id
    return headers


def _client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, headers=_get_headers(), timeout=30)


def _get_with_slug(path: str, slug: str, **extra_params: Any) -> dict[str, Any]:
    """GET with slug as unencoded query param (API requires literal slashes in slug)."""
    qs = f"slug={slug}"
    rest = "&".join(f"{k}={v}" for k, v in extra_params.items() if v is not None)
    if rest:
        qs = f"{qs}&{rest}"
    url = f"{BASE_URL}{path}?{qs}"
    with _client() as c:
        r = c.get(url)
        r.raise_for_status()
        return r.json()


class LegacyGridPageError(RuntimeError):
    """Страница целиком является старой табличной страницей (page_type=grid)."""


def get_page(slug: str, include_content: bool = True, expand_grids: bool = True) -> dict[str, Any]:
    """Get page details by slug (path), e.g. 'scp/docs/my-page'."""
    data = _get_with_slug("/pages", slug)
    if include_content and "id" in data:
        extra = get_page_by_id(str(data["id"]), include_content=True, expand_grids=expand_grids)
        data.update(extra)
    return data


def get_page_by_id(page_id: str, include_content: bool = True, expand_grids: bool = True) -> dict[str, Any]:
    """Get page details by numeric ID."""
    params: dict[str, Any] = {}
    if include_content:
        params["fields"] = "content,breadcrumbs,attributes"
    with _client() as c:
        r = c.get(f"/pages/{page_id}", params=params)
        r.raise_for_status()
        data = r.json()
    if not include_content:
        return data
    if data.get("page_type") == "grid" and data.get("content") is None:
        # Публичный API не отдаёт содержимое старых табличных страниц:
        # пустой ответ иначе выглядит как пустая страница.
        raise LegacyGridPageError(
            f"Страница {data.get('id')} «{data.get('title')}» является старой табличной "
            "страницей (page_type=grid). Публичный API Вики её содержимое не отдаёт; "
            "выгрузите таблицу из интерфейса (⋯ → Экспорт → CSV/XLSX)."
        )
    if expand_grids and data.get("content"):
        data["content"] = expand_inline_grids(data["content"])
    return data


WGRID_RE = re.compile(r'\{%\s*wgrid\s+id="([^"]+)"[^%]*%\}')


def expand_inline_grids(content: str) -> str:
    """Подставить вместо маркеров {% wgrid id="UUID" %} таблицы Markdown.

    Маркер сохраняется над таблицей, чтобы по нему можно было править таблицу
    инструментами wiki_update_grid_cells / wiki_add_grid_rows.
    """
    def repl(m: re.Match) -> str:
        grid_id = m.group(1)
        try:
            table = grid_to_markdown(get_grid(grid_id))
        except Exception as e:  # таблица недоступна: оставить маркер как есть
            return f"{m.group(0)}\n\n(таблица {grid_id} не прочитана: {e})"
        return f"{m.group(0)}\n\n{table}"
    return WGRID_RE.sub(repl, content)


def get_grid(
    grid_id: str,
    only_cols: str | None = None,
    only_rows: str | None = None,
    filter: str | None = None,
    sort: str | None = None,
    revision: int | None = None,
) -> dict[str, Any]:
    """Get dynamic table (grid) by UUID. GET /v1/grids/{uuid}"""
    params = {k: v for k, v in {
        "only_cols": only_cols, "only_rows": only_rows,
        "filter": filter, "sort": sort, "revision": revision,
    }.items() if v is not None}
    with _client() as c:
        r = c.get(f"/grids/{grid_id}", params=params)
        r.raise_for_status()
        return r.json()


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        parts = []
        for v in value:
            if isinstance(v, dict):
                parts.append(str(v.get("display") or v.get("login") or v.get("uid") or v))
            else:
                parts.append(str(v))
        value = ", ".join(parts)
    elif isinstance(value, bool):
        value = "да" if value else "нет"
    return str(value).replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def grid_to_markdown(grid: dict[str, Any], with_row_ids: bool = True) -> str:
    """Convert grid response (structure.columns + rows) to a Markdown table."""
    columns = grid.get("structure", {}).get("columns", [])
    head = [c.get("title") or c.get("slug", "") for c in columns]
    if with_row_ids:
        head = ["row_id"] + head
    lines = ["| " + " | ".join(_cell_text(h) for h in head) + " |",
             "|" + "---|" * len(head)]
    for row in grid.get("rows", []):
        cells = [_cell_text(v) for v in row.get("row", [])]
        if with_row_ids:
            cells = [str(row.get("id", ""))] + cells
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def update_grid_cells(grid_id: str, cells: list[dict[str, Any]], revision: str | None = None) -> dict[str, Any]:
    """Update cells of a grid. POST /v1/grids/{uuid}/cells

    cells: [{"row_id": 1, "column_slug": "status", "value": "..."}]
    """
    body: dict[str, Any] = {"cells": cells}
    if revision is not None:
        body["revision"] = revision
    with _client() as c:
        r = c.post(f"/grids/{grid_id}/cells", json=body)
        r.raise_for_status()
        return r.json()


def add_grid_rows(
    grid_id: str,
    rows: list[dict[str, Any]],
    after_row_id: str | None = None,
    position: int | None = None,
    revision: str | None = None,
) -> dict[str, Any]:
    """Add rows to a grid. POST /v1/grids/{uuid}/rows

    rows: [{"column_slug": value, ...}]
    """
    body: dict[str, Any] = {"rows": rows}
    for k, v in {"after_row_id": after_row_id, "position": position, "revision": revision}.items():
        if v is not None:
            body[k] = v
    with _client() as c:
        r = c.post(f"/grids/{grid_id}/rows", json=body)
        r.raise_for_status()
        return r.json()


def create_page(slug: str, title: str, content: str) -> dict[str, Any]:
    """Create a new page. POST /v1/pages"""
    with _client() as c:
        r = c.post("/pages", json={"slug": slug, "title": title, "content": content})
        r.raise_for_status()
        return r.json()


def update_page(page_id: str, title: str | None, content: str | None) -> dict[str, Any]:
    """Update page title and/or content. POST /v1/pages/{id}"""
    body: dict[str, Any] = {}
    if title is not None:
        body["title"] = title
    if content is not None:
        body["content"] = content
    with _client() as c:
        r = c.post(f"/pages/{page_id}", json=body)
        r.raise_for_status()
        return r.json()


def append_to_page(page_id: str, content: str) -> dict[str, Any]:
    """Append content to existing page. POST /v1/pages/{id}/append-content"""
    with _client() as c:
        r = c.post(
            f"/pages/{page_id}/append-content",
            json={"content": content, "body": {"location": "bottom"}},
        )
        r.raise_for_status()
        return r.json()


def delete_page(page_id: str) -> dict[str, Any]:
    """Delete page by ID. DELETE /v1/pages/{id}"""
    with _client() as c:
        r = c.delete(f"/pages/{page_id}")
        r.raise_for_status()
        return {"deleted": True, "page_id": page_id}


def get_descendants(slug: str, page_size: int = 50, cursor: str | None = None) -> dict[str, Any]:
    """Get descendants (subpages tree) of a page by slug. GET /v1/pages/descendants"""
    params: dict[str, Any] = {"page_size": page_size}
    if cursor:
        params["cursor"] = cursor
    return _get_with_slug("/pages/descendants", slug, **{k: v for k, v in params.items()})


def get_descendants_by_id(page_id: str, page_size: int = 50, cursor: str | None = None) -> dict[str, Any]:
    """Get descendants (subpages tree) of a page by ID. GET /v1/pages/{id}/descendants"""
    params: dict[str, Any] = {"page_size": page_size}
    if cursor:
        params["cursor"] = cursor
    with _client() as c:
        r = c.get(f"/pages/{page_id}/descendants", params=params)
        r.raise_for_status()
        return r.json()


def get_comments(page_id: str) -> dict[str, Any]:
    """Get comments for a page. GET /v1/pages/{id}/comments"""
    with _client() as c:
        r = c.get(f"/pages/{page_id}/comments")
        r.raise_for_status()
        return r.json()


def add_comment(page_id: str, text: str) -> dict[str, Any]:
    """Add a comment to a page. POST /v1/pages/{id}/comments"""
    with _client() as c:
        r = c.post(f"/pages/{page_id}/comments", json={"text": text})
        r.raise_for_status()
        return r.json()


def get_page_attachments(page_id: str) -> dict[str, Any]:
    """Get attachments for a page. GET /v1/pages/{id}/attachments"""
    with _client() as c:
        r = c.get(f"/pages/{page_id}/attachments")
        r.raise_for_status()
        return r.json()


def get_current_user() -> dict[str, Any]:
    """Get current authenticated user info. GET /v1/users/me"""
    with _client() as c:
        r = c.get("/users/me")
        r.raise_for_status()
        return r.json()
