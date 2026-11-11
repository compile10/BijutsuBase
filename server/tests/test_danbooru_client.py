"""Tests for the Danbooru client and its handling in booru enrichment."""

import unittest
from types import SimpleNamespace
from unittest import mock

import httpx

from sources.booru_enrichment import enrich_file_from_boorus
from sources.danbooru.danbooru_client import DanbooruClient
from sources.danbooru.errors import DanbooruApiError


def make_client(handler) -> DanbooruClient:
    return DanbooruClient(transport=httpx.MockTransport(handler))


class DanbooruClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_post_wraps_single_post(self) -> None:
        def handle_request(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.params["md5"], "abc123")
            return httpx.Response(200, json={"id": 42})

        posts = await make_client(handle_request).get_post("abc123")

        self.assertEqual([post.id for post in posts], [42])

    async def test_get_post_returns_empty_on_miss(self) -> None:
        for response in (httpx.Response(404), httpx.Response(200, json=[])):
            with self.subTest(status=response.status_code):
                client = make_client(lambda request, response=response: response)

                self.assertEqual(await client.get_post("abc123"), [])

    async def test_get_post_raises_on_failures(self) -> None:
        def raise_connect_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused", request=request)

        handlers = {
            "server error": lambda request: httpx.Response(503),
            "forbidden": lambda request: httpx.Response(403),
            "connection error": raise_connect_error,
            "html page": lambda request: httpx.Response(200, text="<html>maintenance</html>"),
            "unexpected type": lambda request: httpx.Response(200, json="nope"),
            "invalid post": lambda request: httpx.Response(200, json=[{"tag_string": "1girl"}]),
        }

        for name, handler in handlers.items():
            with self.subTest(name):
                with self.assertRaises(DanbooruApiError):
                    await make_client(handler).get_post("abc123")


class DanbooruEnrichmentTests(unittest.IsolatedAsyncioTestCase):
    async def test_danbooru_errors_fall_through_to_gelbooru(self) -> None:
        file = SimpleNamespace(sha256_hash="f" * 64, md5_hash="abc123")
        fetch_gelbooru = mock.AsyncMock(return_value=None)

        with (
            mock.patch("sources.booru_enrichment.DanbooruClient") as danbooru,
            mock.patch("sources.booru_enrichment.fetch_gelbooru_metadata", fetch_gelbooru),
            self.assertLogs("sources.booru_enrichment", level="WARNING") as captured,
        ):
            danbooru.return_value.get_post = mock.AsyncMock(
                side_effect=DanbooruApiError("Danbooru returned 503 for MD5 abc123")
            )
            enriched = await enrich_file_from_boorus(file, mock.MagicMock())

        self.assertFalse(enriched)
        fetch_gelbooru.assert_awaited_once_with("abc123")
        self.assertIn("Danbooru returned 503", "\n".join(captured.output))


if __name__ == "__main__":
    unittest.main()
