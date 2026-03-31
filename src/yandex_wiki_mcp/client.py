"""Yandex Wiki API client."""

import os
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


def get_page(slug: str, include_content: bool = True) -> dict[str, Any]:
    """Get page details by slug (path), e.g. 'scp/docs/my-page'."""
    data = _get_with_slug("/pages", slug)
    if include_content and "id" in data:
        extra = get_page_by_id(str(data["id"]), include_content=True)
        data.update(extra)
    return data


def get_page_by_id(page_id: str, include_content: bool = True) -> dict[str, Any]:
    """Get page details by numeric ID."""
    params: dict[str, Any] = {}
    if include_content:
        params["fields"] = "content,breadcrumbs,attributes"
    with _client() as c:
        r = c.get(f"/pages/{page_id}", params=params)
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
        r = c.post(f"/pages/{page_id}/append-content", json={"content": content})
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
