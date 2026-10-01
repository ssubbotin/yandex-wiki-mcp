import json
import unittest
from unittest.mock import patch

import httpx

from yandex_wiki_mcp import client


class AppendToPageTests(unittest.TestCase):
    def test_append_to_page_posts_content_to_page_bottom(self) -> None:
        requests: list[httpx.Request] = []
        response_data = {"id": 42, "slug": "docs/example", "title": "Example"}

        def handle_request(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=response_data)

        transport = httpx.MockTransport(handle_request)
        http_client = httpx.Client(base_url=client.BASE_URL, transport=transport)

        with patch.object(client, "_client", return_value=http_client):
            result = client.append_to_page("42", "New content")

        self.assertEqual(result, response_data)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(requests[0].url.path, "/v1/pages/42/append-content")
        self.assertEqual(
            json.loads(requests[0].content),
            {
                "content": "New content",
                "body": {"location": "bottom"},
            },
        )


def _mock(handler):
    transport = httpx.MockTransport(handler)
    return lambda: httpx.Client(base_url=client.BASE_URL, transport=transport)


GRID = {
    "id": "b76d7054-8169-404d-8b10-67293930f117",
    "title": "plan",
    "revision": "28",
    "structure": {"columns": [
        {"slug": "name", "title": "Работа"},
        {"slug": "who", "title": "Исполнитель"},
    ]},
    "rows": [
        {"id": "1", "row": ["Строка 1\nвторая | часть", [{"display": "Антон"}]]},
        {"id": "3", "row": [None, True]},
    ],
}


class GridTests(unittest.TestCase):
    def test_get_grid_passes_filters(self) -> None:
        requests: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json=GRID)

        with patch.object(client, "_client", side_effect=_mock(handle)):
            client.get_grid(GRID["id"], only_cols="name", sort="-name")

        self.assertEqual(requests[0].url.path, f"/v1/grids/{GRID['id']}")
        self.assertEqual(dict(requests[0].url.params), {"only_cols": "name", "sort": "-name"})

    def test_grid_to_markdown(self) -> None:
        self.assertEqual(
            client.grid_to_markdown(GRID).splitlines(),
            [
                "| row_id | Работа | Исполнитель |",
                "|---|---|---|",
                "| 1 | Строка 1<br>вторая \\| часть | Антон |",
                "| 3 |  | да |",
            ],
        )

    def test_page_content_expands_inline_grids(self) -> None:
        page = {"id": 7, "page_type": "page",
                "content": f'До\n{{% wgrid id="{GRID["id"]}" %}}\nПосле'}

        def handle(request: httpx.Request) -> httpx.Response:
            if request.url.path.startswith("/v1/grids/"):
                return httpx.Response(200, json=GRID)
            return httpx.Response(200, json=page)

        with patch.object(client, "_client", side_effect=_mock(handle)):
            content = client.get_page_by_id("7")["content"]
            raw = client.get_page_by_id("7", expand_grids=False)["content"]

        self.assertIn(f'{{% wgrid id="{GRID["id"]}" %}}\n\n| row_id | Работа | Исполнитель |', content)
        self.assertTrue(content.endswith("После"))
        self.assertEqual(raw, page["content"])

    def test_legacy_grid_page_raises_clear_error(self) -> None:
        page = {"id": 49348131, "title": "Матрица", "page_type": "grid", "content": None}

        with patch.object(client, "_client", side_effect=_mock(lambda r: httpx.Response(200, json=page))):
            with self.assertRaises(client.LegacyGridPageError):
                client.get_page_by_id("49348131")
            meta = client.get_page_by_id("49348131", include_content=False)

        self.assertEqual(meta["page_type"], "grid")

    def test_update_cells_and_add_rows_bodies(self) -> None:
        requests: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"revision": "29"})

        cells = [{"row_id": 1, "column_slug": "who", "value": "[RLMKX-1](https://tracker.yandex.ru/RLMKX-1)"}]
        with patch.object(client, "_client", side_effect=_mock(handle)):
            client.update_grid_cells(GRID["id"], cells, revision="28")
            client.add_grid_rows(GRID["id"], [{"name": "Новая"}], after_row_id="3")

        self.assertEqual(requests[0].url.path, f"/v1/grids/{GRID['id']}/cells")
        self.assertEqual(json.loads(requests[0].content), {"cells": cells, "revision": "28"})
        self.assertEqual(requests[1].url.path, f"/v1/grids/{GRID['id']}/rows")
        self.assertEqual(json.loads(requests[1].content), {"rows": [{"name": "Новая"}], "after_row_id": "3"})


class AuthHeaderTests(unittest.TestCase):
    def test_oauth_token_has_priority_over_iam(self) -> None:
        env = {"WIKI_OAUTH_TOKEN": "y0_oauth", "WIKI_IAM_TOKEN": "t1.iam", "WIKI_CLOUD_ORG_ID": "org"}
        with patch.dict(client.os.environ, env, clear=True):
            self.assertEqual(
                client._get_headers(),
                {"Authorization": "OAuth y0_oauth", "X-Cloud-Org-Id": "org"},
            )

    def test_tracker_oauth_fallback_and_iam_default(self) -> None:
        with patch.dict(client.os.environ, {"TRACKER_OAUTH_TOKEN": "y0_tr"}, clear=True):
            self.assertEqual(client._get_headers(), {"Authorization": "OAuth y0_tr"})
        with patch.dict(client.os.environ, {"WIKI_IAM_TOKEN": "t1.iam"}, clear=True):
            self.assertEqual(client._get_headers(), {"Authorization": "Bearer t1.iam"})

    def test_missing_tokens_raise(self) -> None:
        with patch.dict(client.os.environ, {}, clear=True):
            with self.assertRaises(RuntimeError):
                client._get_headers()


class TrackerTokenFallbackTests(unittest.TestCase):
    def test_tracker_mcp_token_name_is_accepted(self) -> None:
        env = {"TRACKER_TOKEN": "y0_tr", "TRACKER_CLOUD_ORG_ID": "org"}
        with patch.dict(client.os.environ, env, clear=True):
            self.assertEqual(
                client._get_headers(),
                {"Authorization": "OAuth y0_tr", "X-Cloud-Org-Id": "org"},
            )


class ApiErrorTests(unittest.TestCase):
    def test_error_text_carries_api_explanation(self) -> None:
        body = {"error_code": "BAD_REQUEST", "debug_message": "Unknown field authors"}
        with patch.object(client, "_client", side_effect=_mock(lambda r: httpx.Response(400, json=body))):
            with self.assertRaises(client.WikiApiError) as ctx:
                client.get_page_by_id("7")
        self.assertIn("400 GET /v1/pages/7", str(ctx.exception))
        self.assertIn("BAD_REQUEST; Unknown field authors", str(ctx.exception))


class SearchAndRevisionTests(unittest.TestCase):
    def test_search_body(self) -> None:
        requests: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"results": []})

        with patch.object(client, "_client", side_effect=_mock(handle)):
            client.search("водность", limit=5, doc_type="page")

        self.assertEqual(requests[0].method, "POST")
        self.assertEqual(requests[0].url.path, "/v1/search")
        self.assertEqual(
            json.loads(requests[0].content),
            {"query": "водность", "limit": 5, "cursor": 1, "highlight": False, "filters": {"type": "page"}},
        )

    def test_revisions_and_old_revision_read(self) -> None:
        requests: list[httpx.Request] = []

        def handle(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            return httpx.Response(200, json={"id": 7, "page_type": "page", "content": "x", "results": []})

        with patch.object(client, "_client", side_effect=_mock(handle)):
            client.get_revisions("7", page_size=2, cursor="abc")
            client.get_page_by_id("7", revision_id=74682203)

        self.assertEqual(requests[0].url.path, "/v1/pages/7/revisions")
        self.assertEqual(dict(requests[0].url.params), {"page_size": "2", "cursor": "abc"})
        self.assertEqual(requests[1].url.params["revision_id"], "74682203")


if __name__ == "__main__":
    unittest.main()
