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


if __name__ == "__main__":
    unittest.main()
