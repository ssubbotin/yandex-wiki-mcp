"""MCP server definition for Yandex Wiki."""

import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from . import client


app = Server("yandex-wiki-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="wiki_get_page",
            description=(
                "Get Yandex Wiki page by slug (path from URL). "
                "Returns title, id, content and breadcrumbs. Dynamic tables "
                "({% wgrid id=\"UUID\" %}) are expanded into Markdown tables below the marker. "
                "Example slug: 'scp/arxitektura-i-infrastruktura/adr/my-adr'"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Page slug/path from URL"},
                    "include_content": {
                        "type": "boolean",
                        "description": "Include page content (default true)",
                        "default": True,
                    },
                    "expand_grids": {
                        "type": "boolean",
                        "description": "Expand dynamic tables into Markdown (default true)",
                        "default": True,
                    },
                },
                "required": ["slug"],
            },
        ),
        Tool(
            name="wiki_get_page_by_id",
            description=(
                "Get Yandex Wiki page by numeric ID. Returns title, slug, content, breadcrumbs "
                "and attributes. Dynamic tables are expanded into Markdown like in wiki_get_page."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                    "include_content": {
                        "type": "boolean",
                        "description": "Include page content (default true)",
                        "default": True,
                    },
                    "expand_grids": {
                        "type": "boolean",
                        "description": "Expand dynamic tables into Markdown (default true)",
                        "default": True,
                    },
                    "revision_id": {
                        "type": "integer",
                        "description": "Read the page as of this revision (ids from wiki_get_revisions)",
                    },
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="wiki_get_descendants",
            description=(
                "Get descendants (subpages tree) of a page by slug. "
                "Use this to explore the page hierarchy."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {"type": "string", "description": "Parent page slug/path"},
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results (default 50)",
                        "default": 50,
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor from previous response",
                    },
                },
                "required": ["slug"],
            },
        ),
        Tool(
            name="wiki_get_descendants_by_id",
            description="Get descendants (subpages tree) of a page by numeric ID.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results (default 50)",
                        "default": 50,
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Pagination cursor from previous response",
                    },
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="wiki_create_page",
            description="Create a new Yandex Wiki page",
            inputSchema={
                "type": "object",
                "properties": {
                    "slug": {
                        "type": "string",
                        "description": "Full page slug/path (e.g. 'users/john/new-page')",
                    },
                    "title": {"type": "string", "description": "Page title"},
                    "content": {
                        "type": "string",
                        "description": "Page content in Wiki markup",
                    },
                },
                "required": ["slug", "title", "content"],
            },
        ),
        Tool(
            name="wiki_update_page",
            description="Update title and/or content of an existing Yandex Wiki page",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                    "title": {
                        "type": "string",
                        "description": "New title (omit to keep current)",
                    },
                    "content": {
                        "type": "string",
                        "description": "New full content (omit to keep current)",
                    },
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="wiki_append_to_page",
            description="Append content to the end of an existing Yandex Wiki page",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                    "content": {"type": "string", "description": "Content to append"},
                },
                "required": ["page_id", "content"],
            },
        ),
        Tool(
            name="wiki_delete_page",
            description="Delete a Yandex Wiki page by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="wiki_get_comments",
            description="Get comments for a Yandex Wiki page",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="wiki_add_comment",
            description="Add a comment to a Yandex Wiki page",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                    "text": {"type": "string", "description": "Comment text"},
                },
                "required": ["page_id", "text"],
            },
        ),
        Tool(
            name="wiki_get_attachments",
            description="Get list of files attached to a Yandex Wiki page",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="wiki_search",
            description=(
                "Full-text search over Yandex Wiki. Returns slug, title, url, a content snippet "
                "and modified_at per hit; paginate with cursor (page number, 1..500)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "limit": {"type": "integer", "description": "Results per page, 1..50 (default 10)", "default": 10},
                    "cursor": {"type": "integer", "description": "Result page number (default 1)", "default": 1},
                    "type": {"type": "string", "enum": ["page", "file"], "description": "Only pages or only files"},
                    "highlight": {"type": "boolean", "description": "Wrap matches in <em>", "default": False},
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="wiki_get_revisions",
            description=(
                "Revision history of a page by numeric ID: revision id, author, created_at, newest first. "
                "Pass a revision id to wiki_get_page_by_id to read that version."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                    "page_size": {"type": "integer", "description": "Revisions per page (default 20)", "default": 20},
                    "cursor": {"type": "string", "description": "Pagination cursor from previous response"},
                },
                "required": ["page_id"],
            },
        ),
        Tool(
            name="wiki_get_grid",
            description=(
                "Get a dynamic table (grid) by UUID, the id from {% wgrid id=\"UUID\" %} on a page. "
                "Returns a Markdown table with a row_id column (format=markdown, default) "
                "or the raw API response with column slugs (format=json)."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "grid_id": {"type": "string", "description": "Grid UUID"},
                    "format": {
                        "type": "string",
                        "enum": ["markdown", "json"],
                        "default": "markdown",
                    },
                    "only_cols": {"type": "string", "description": "Column slugs, comma-separated"},
                    "only_rows": {"type": "string", "description": "Row ids, comma-separated"},
                    "filter": {"type": "string", "description": "Row filter, e.g. '[slug] ~ wiki AND [slug2]<32'"},
                    "sort": {"type": "string", "description": "Sort by columns, e.g. 'slug, -slug2'"},
                    "revision": {"type": "integer", "description": "Load an older grid revision"},
                },
                "required": ["grid_id"],
            },
        ),
        Tool(
            name="wiki_update_grid_cells",
            description=(
                "Update cells of a dynamic table. Column slugs come from wiki_get_grid with format=json; "
                "values are Wiki markup strings (links [text](url) work), numbers, booleans or lists."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "grid_id": {"type": "string", "description": "Grid UUID"},
                    "cells": {
                        "type": "array",
                        "description": "Cells to update",
                        "items": {
                            "type": "object",
                            "properties": {
                                "row_id": {"type": "integer"},
                                "column_slug": {"type": "string"},
                                "value": {},
                            },
                            "required": ["row_id", "column_slug", "value"],
                        },
                    },
                    "revision": {"type": "string", "description": "Expected grid revision (optimistic lock)"},
                },
                "required": ["grid_id", "cells"],
            },
        ),
        Tool(
            name="wiki_add_grid_rows",
            description="Add rows to a dynamic table. Each row is an object {column_slug: value}.",
            inputSchema={
                "type": "object",
                "properties": {
                    "grid_id": {"type": "string", "description": "Grid UUID"},
                    "rows": {"type": "array", "items": {"type": "object"}},
                    "after_row_id": {"type": "string", "description": "Insert after this row id"},
                    "position": {"type": "integer", "description": "Insert at this position"},
                    "revision": {"type": "string", "description": "Expected grid revision (optimistic lock)"},
                },
                "required": ["grid_id", "rows"],
            },
        ),
        Tool(
            name="wiki_get_current_user",
            description="Get info about the currently authenticated Yandex Wiki user",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


def _ok(data: dict) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(data, ensure_ascii=False, indent=2))]


def _err(e: Exception) -> list[TextContent]:
    return [TextContent(type="text", text=f"Error: {e}")]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        match name:
            case "wiki_get_page":
                return _ok(client.get_page(
                    arguments["slug"],
                    arguments.get("include_content", True),
                    arguments.get("expand_grids", True),
                ))
            case "wiki_get_page_by_id":
                return _ok(client.get_page_by_id(
                    arguments["page_id"],
                    arguments.get("include_content", True),
                    arguments.get("expand_grids", True),
                    arguments.get("revision_id"),
                ))
            case "wiki_get_descendants":
                return _ok(client.get_descendants(
                    arguments["slug"],
                    arguments.get("page_size", 50),
                    arguments.get("cursor"),
                ))
            case "wiki_get_descendants_by_id":
                return _ok(client.get_descendants_by_id(
                    arguments["page_id"],
                    arguments.get("page_size", 50),
                    arguments.get("cursor"),
                ))
            case "wiki_create_page":
                return _ok(client.create_page(
                    arguments["slug"],
                    arguments["title"],
                    arguments["content"],
                ))
            case "wiki_update_page":
                return _ok(client.update_page(
                    arguments["page_id"],
                    arguments.get("title"),
                    arguments.get("content"),
                ))
            case "wiki_append_to_page":
                return _ok(client.append_to_page(
                    arguments["page_id"],
                    arguments["content"],
                ))
            case "wiki_delete_page":
                return _ok(client.delete_page(arguments["page_id"]))
            case "wiki_get_comments":
                return _ok(client.get_comments(arguments["page_id"]))
            case "wiki_add_comment":
                return _ok(client.add_comment(arguments["page_id"], arguments["text"]))
            case "wiki_get_attachments":
                return _ok(client.get_page_attachments(arguments["page_id"]))
            case "wiki_search":
                return _ok(client.search(
                    arguments["query"],
                    arguments.get("limit", 10),
                    arguments.get("cursor", 1),
                    arguments.get("type"),
                    arguments.get("highlight", False),
                ))
            case "wiki_get_revisions":
                return _ok(client.get_revisions(
                    arguments["page_id"],
                    arguments.get("page_size", 20),
                    arguments.get("cursor"),
                ))
            case "wiki_get_grid":
                grid = client.get_grid(
                    arguments["grid_id"],
                    arguments.get("only_cols"),
                    arguments.get("only_rows"),
                    arguments.get("filter"),
                    arguments.get("sort"),
                    arguments.get("revision"),
                )
                if arguments.get("format", "markdown") == "json":
                    return _ok(grid)
                head = f"# {grid.get('title', '')} (revision {grid.get('revision')})\n\n"
                return [TextContent(type="text", text=head + client.grid_to_markdown(grid))]
            case "wiki_update_grid_cells":
                return _ok(client.update_grid_cells(
                    arguments["grid_id"],
                    arguments["cells"],
                    arguments.get("revision"),
                ))
            case "wiki_add_grid_rows":
                return _ok(client.add_grid_rows(
                    arguments["grid_id"],
                    arguments["rows"],
                    arguments.get("after_row_id"),
                    arguments.get("position"),
                    arguments.get("revision"),
                ))
            case "wiki_get_current_user":
                return _ok(client.get_current_user())
            case _:
                return _err(ValueError(f"Unknown tool: {name}"))
    except Exception as e:
        return _err(e)


async def run():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())
