"""Tests for resolving Danbooru post URLs to original media."""

import unittest

import httpx

from sources.danbooru.url_resolver import (
    DanbooruPostUnavailableError,
    get_danbooru_post_id,
    resolve_danbooru_post_url,
)


class GetDanbooruPostIdTests(unittest.TestCase):
    def test_extracts_post_id_and_ignores_query(self) -> None:
        url = (
            "https://danbooru.donmai.us/posts/11807317"
            "?q=monitoring_%28vocaloid%29+"
        )

        self.assertEqual(get_danbooru_post_id(url), 11807317)

    def test_rejects_non_post_url(self) -> None:
        self.assertIsNone(
            get_danbooru_post_id("https://danbooru.donmai.us/posts?tags=hatsune_miku")
        )


class ResolveDanbooruPostUrlTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolves_original_file_url_through_json_api(self) -> None:
        original_url = "https://cdn.donmai.us/original/c4/29/image.jpg"

        def handle_request(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.path, "/posts/11807317.json")
            self.assertEqual(request.url.query, b"")
            return httpx.Response(200, json={"id": 11807317, "file_url": original_url})

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handle_request)
        ) as client:
            resolved_url = await resolve_danbooru_post_url(
                "https://danbooru.donmai.us/posts/11807317?q=ignored",
                client,
            )

        self.assertEqual(resolved_url, original_url)

    async def test_leaves_direct_file_url_unchanged(self) -> None:
        direct_url = "https://cdn.donmai.us/original/c4/29/image.jpg"

        def fail_on_request(request: httpx.Request) -> httpx.Response:
            self.fail(f"Unexpected request to {request.url}")

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(fail_on_request)
        ) as client:
            resolved_url = await resolve_danbooru_post_url(direct_url, client)

        self.assertEqual(resolved_url, direct_url)

    async def test_rejects_post_without_accessible_original(self) -> None:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"id": 11807317})
            )
        ) as client:
            with self.assertRaisesRegex(
                DanbooruPostUnavailableError,
                "does not have an accessible original file",
            ):
                await resolve_danbooru_post_url(
                    "https://danbooru.donmai.us/posts/11807317",
                    client,
                )


if __name__ == "__main__":
    unittest.main()
