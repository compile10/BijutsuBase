"""Tests for resolving Gelbooru post URLs to original media."""

import unittest

import httpx

from sources.gelbooru.errors import (
    GelbooruApiError,
    GelbooruNotConfiguredError,
    GelbooruPostUnavailableError,
)
from sources.gelbooru.gelbooru_client import GelbooruClient
from sources.gelbooru.url_resolver import (
    get_gelbooru_post_id,
    resolve_gelbooru_post_url,
)

POST_URL = "https://gelbooru.com/index.php?page=post&s=view&id=9876543&tags=hatsune_miku"


def make_client(handler) -> GelbooruClient:
    return GelbooruClient(
        api_key="secret-key",
        user_id="123",
        transport=httpx.MockTransport(handler),
    )


class GetGelbooruPostIdTests(unittest.TestCase):
    def test_extracts_post_id_regardless_of_param_order(self) -> None:
        self.assertEqual(get_gelbooru_post_id(POST_URL), 9876543)
        self.assertEqual(
            get_gelbooru_post_id("https://www.gelbooru.com/index.php?id=5&s=view&page=post"),
            5,
        )

    def test_rejects_non_post_urls(self) -> None:
        for url in (
            "https://gelbooru.com/index.php?page=post&s=list&tags=hatsune_miku",
            "https://gelbooru.com/index.php?page=post&s=view&id=abc",
            "https://gelbooru.com/index.php?page=post&s=view",
            "https://gelbooru.com/index.php?page=post&s=view&id=%C2%B2",
            "https://gelbooru.com/index.php?page=post&s=view&id=%D9%A1",
            "https://img3.gelbooru.com/images/aa/bb/aabb.jpg",
            "https://evil.example/index.php?page=post&s=view&id=1",
        ):
            with self.subTest(url=url):
                self.assertIsNone(get_gelbooru_post_id(url))


class ResolveGelbooruPostUrlTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolves_original_file_url_through_dapi(self) -> None:
        original_url = "https://img3.gelbooru.com/images/aa/bb/aabb.jpg"

        def handle_request(request: httpx.Request) -> httpx.Response:
            params = request.url.params
            self.assertEqual(params["s"], "post")
            self.assertEqual(params["id"], "9876543")
            self.assertEqual(params["api_key"], "secret-key")
            self.assertNotIn("tags", params)
            return httpx.Response(
                200,
                json={"post": [{"id": 9876543, "file_url": original_url}]},
            )

        resolved_url = await resolve_gelbooru_post_url(POST_URL, make_client(handle_request))

        self.assertEqual(resolved_url, original_url)

    async def test_leaves_other_urls_unchanged(self) -> None:
        direct_url = "https://img3.gelbooru.com/images/aa/bb/aabb.jpg"

        def fail_on_request(request: httpx.Request) -> httpx.Response:
            self.fail(f"Unexpected request to {request.url}")

        resolved_url = await resolve_gelbooru_post_url(direct_url, make_client(fail_on_request))

        self.assertEqual(resolved_url, direct_url)

    async def test_requires_credentials(self) -> None:
        unconfigured = GelbooruClient(api_key=None, user_id=None)
        unconfigured.api_key = None
        unconfigured.user_id = None

        with self.assertRaisesRegex(GelbooruNotConfiguredError, "GELBOORU_API_KEY"):
            await resolve_gelbooru_post_url(POST_URL, unconfigured)

    async def test_missing_post_is_unavailable(self) -> None:
        client = make_client(lambda request: httpx.Response(200, json={"@attributes": {"count": 0}}))

        with self.assertRaisesRegex(GelbooruPostUnavailableError, "was not found"):
            await resolve_gelbooru_post_url(POST_URL, client)

    async def test_post_without_file_url_is_unavailable(self) -> None:
        client = make_client(lambda request: httpx.Response(200, json={"post": [{"id": 9876543}]}))

        with self.assertRaisesRegex(GelbooruPostUnavailableError, "accessible original file"):
            await resolve_gelbooru_post_url(POST_URL, client)

    async def test_rejected_credentials_are_api_errors_without_key(self) -> None:
        client = make_client(lambda request: httpx.Response(401, text="Unauthorized"))

        with self.assertRaises(GelbooruApiError) as context:
            await resolve_gelbooru_post_url(POST_URL, client)

        self.assertIn("credentials", str(context.exception))
        self.assertNotIn("secret-key", str(context.exception))

    async def test_rate_limiting_is_api_error(self) -> None:
        client = make_client(lambda request: httpx.Response(429, text="Too Many Requests"))

        with self.assertRaisesRegex(GelbooruApiError, "429"):
            await resolve_gelbooru_post_url(POST_URL, client)

    async def test_connection_errors_redact_api_key(self) -> None:
        def raise_connect_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError(f"cannot connect to {request.url}", request=request)

        with self.assertRaises(GelbooruApiError) as context:
            await resolve_gelbooru_post_url(POST_URL, make_client(raise_connect_error))

        self.assertIsNone(context.exception.__cause__)
        self.assertNotIn("secret-key", str(context.exception))
        self.assertIn("api_key=[REDACTED]", str(context.exception))

    async def test_invalid_json_is_api_error(self) -> None:
        client = make_client(lambda request: httpx.Response(200, text="<html>"))

        with self.assertRaisesRegex(GelbooruApiError, "invalid JSON"):
            await resolve_gelbooru_post_url(POST_URL, client)


if __name__ == "__main__":
    unittest.main()
