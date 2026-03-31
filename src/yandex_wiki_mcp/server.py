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
                "Returns title, id, content and breadcrumbs. "
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
                },
                "required": ["slug"],
            },
        ),
        Tool(
            name="wiki_get_page_by_id",
            description="Get Yandex Wiki page by numeric ID. Returns title, slug, content, breadcrumbs and attributes.",
            inputSchema={
                "type": "object",
                "properties": {
                    "page_id": {"type": "string", "description": "Numeric page ID"},
                    "include_content": {
                        "type": "boolean",
                        "description": "Include page content (default true)",
                        "default": True,
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
                ))
            case "wiki_get_page_by_id":
                return _ok(client.get_page_by_id(
                    arguments["page_id"],
                    arguments.get("include_content", True),
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
            case "wiki_get_current_user":
                return _ok(client.get_current_user())
            case _:
                return _err(ValueError(f"Unknown tool: {name}"))
    except Exception as e:
        return _err(e)


async def run():
    async with stdio_server() as streams:
        await app.run(streams[0], streams[1], app.create_initialization_options())
