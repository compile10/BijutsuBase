"""Tests for the Gelbooru fallback client and tag categorization."""

import unittest
from types import SimpleNamespace
from unittest import mock

import httpx

from api.serializers.gelbooru import GelbooruPost
from models.tag import TagCategory
from sources.gelbooru.enrich_file import (
    categorize_gelbooru_tags,
    get_gelbooru_source,
    get_gelbooru_tag_names,
)
from sources.gelbooru.gelbooru_client import GelbooruClient
from sources.tag_utils import TAG_NAME_MAX_LENGTH, associate_tags


def make_client(handler) -> GelbooruClient:
    return GelbooruClient(
        api_key="key",
        user_id="123",
        transport=httpx.MockTransport(handler),
    )


class GelbooruClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_post_sends_md5_search_with_credentials(self) -> None:
        def handle_request(request: httpx.Request) -> httpx.Response:
            params = request.url.params
            self.assertEqual(params["s"], "post")
            self.assertEqual(params["tags"], "md5:abc123")
            self.assertEqual(params["api_key"], "key")
            self.assertEqual(params["user_id"], "123")
            self.assertEqual(params["json"], "1")
            return httpx.Response(
                200,
                json={
                    "@attributes": {"limit": 100, "offset": 0, "count": 1},
                    "post": [
                        {
                            "id": 42,
                            "md5": "abc123",
                            "tags": "1girl hatsune_miku",
                            "rating": "sensitive",
                            "source": "https://example.com/art",
                        }
                    ],
                },
            )

        posts = await make_client(handle_request).get_post("abc123")

        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0].id, 42)
        self.assertEqual(posts[0].rating, "sensitive")

    async def test_get_post_returns_empty_when_post_key_missing(self) -> None:
        def handle_request(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"@attributes": {"count": 0}})

        self.assertEqual(await make_client(handle_request).get_post("abc123"), [])

    async def test_get_post_returns_empty_on_unauthorized(self) -> None:
        def handle_request(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="")

        self.assertEqual(await make_client(handle_request).get_post("abc123"), [])

    async def test_unconfigured_client_skips_requests(self) -> None:
        def fail_on_request(request: httpx.Request) -> httpx.Response:
            self.fail(f"Unexpected request to {request.url}")

        with mock.patch.dict("os.environ", {}, clear=True):
            client = GelbooruClient(transport=httpx.MockTransport(fail_on_request))

        self.assertFalse(client.is_configured)
        self.assertEqual(await client.get_post("abc123"), [])
        self.assertIsNone(await client.get_tag_types(["1girl"]))

    async def test_get_tag_types_batches_and_unescapes(self) -> None:
        requested_batches: list[list[str]] = []

        def handle_request(request: httpx.Request) -> httpx.Response:
            names = request.url.params["names"].split(" ")
            requested_batches.append(names)
            return httpx.Response(
                200,
                json={"tag": [{"id": i, "name": name.replace("'", "&#039;"), "type": 4} for i, name in enumerate(names)]},
            )

        tag_names = [f"tag_{index}" for index in range(150)] + ["girls'_frontline"]
        tag_types = await make_client(handle_request).get_tag_types(tag_names)

        self.assertEqual([len(batch) for batch in requested_batches], [100, 51])
        self.assertEqual(tag_types["girls'_frontline"], 4)
        self.assertEqual(len(tag_types), 151)

    async def test_non_numeric_tag_type_fails_the_lookup(self) -> None:
        def handle_request(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={"tag": [{"id": 1, "name": "artist_a", "count": 12, "type": "artist"}]},
            )

        self.assertIsNone(await make_client(handle_request).get_tag_types(["artist_a"]))

    async def test_malformed_responses_are_treated_as_misses(self) -> None:
        def handle_request(request: httpx.Request) -> httpx.Response:
            if request.url.params["s"] == "post":
                return httpx.Response(200, json={"post": [{"tags": "1girl"}]})
            return httpx.Response(200, text="<html>maintenance</html>")

        client = make_client(handle_request)

        self.assertEqual(await client.get_post("abc123"), [])
        self.assertIsNone(await client.get_tag_types(["1girl"]))

    async def test_unusable_tag_envelopes_fail_the_lookup(self) -> None:
        unusable_payloads = [
            [],
            None,
            {"success": False},
            {"@attributes": {"count": 0}},
            {"tag": "1girl"},
            {"tag": [1, 2]},
        ]

        for payload in unusable_payloads:
            with self.subTest(payload=payload):
                def handle_request(request: httpx.Request, payload=payload) -> httpx.Response:
                    return httpx.Response(200, json=payload)

                self.assertIsNone(await make_client(handle_request).get_tag_types(["1girl"]))

    async def test_malformed_post_items_are_treated_as_misses(self) -> None:
        for payload in [[], {"post": ["not-an-object"]}, {"post": 5}]:
            with self.subTest(payload=payload):
                def handle_request(request: httpx.Request, payload=payload) -> httpx.Response:
                    return httpx.Response(200, json=payload)

                self.assertEqual(await make_client(handle_request).get_post("abc123"), [])

    async def test_post_without_tags_skips_tag_lookup(self) -> None:
        def fail_on_request(request: httpx.Request) -> httpx.Response:
            self.fail(f"Unexpected request to {request.url}")

        self.assertEqual(await make_client(fail_on_request).get_tag_types([]), {})

    async def test_get_tag_types_returns_none_on_error(self) -> None:
        def handle_request(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        self.assertIsNone(await make_client(handle_request).get_tag_types(["1girl"]))


    async def test_logs_do_not_contain_api_key(self) -> None:
        def handle_request(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503)

        client = GelbooruClient(
            api_key="secret-key",
            user_id="123",
            transport=httpx.MockTransport(handle_request),
        )

        with self.assertLogs(level="INFO") as captured:
            await client.get_tag_types(["1girl"])

        output = "\n".join(captured.output)
        self.assertIn("api_key=[REDACTED]", output)
        self.assertNotIn("secret-key", output)


class AssociateTagsTests(unittest.IsolatedAsyncioTestCase):
    async def test_skips_names_longer_than_the_tag_column(self) -> None:
        db = mock.MagicMock()
        file = SimpleNamespace(sha256_hash="f" * 64)

        with self.assertLogs("sources.tag_utils", level="WARNING"):
            await associate_tags(file, db, ["x" * (TAG_NAME_MAX_LENGTH + 1)], TagCategory.GENERAL)

        db.begin_nested.assert_not_called()
        db.add.assert_not_called()


class GelbooruMetadataTests(unittest.TestCase):
    def test_tag_names_are_unescaped(self) -> None:
        post = GelbooruPost(id=1, tags="1girl girls&#039;_frontline  m4a1_(girls&#039;_frontline)")

        self.assertEqual(
            get_gelbooru_tag_names(post),
            ["1girl", "girls'_frontline", "m4a1_(girls'_frontline)"],
        )

    def test_categorize_maps_types_and_defaults_to_general(self) -> None:
        tags_by_category = categorize_gelbooru_tags(
            ["1girl", "artist_a", "series", "char", "highres", "old_tag", "unknown"],
            {"1girl": 0, "artist_a": 1, "series": 3, "char": 4, "highres": 5, "old_tag": 6},
        )

        self.assertEqual(
            tags_by_category,
            {
                TagCategory.GENERAL: ["1girl", "old_tag", "unknown"],
                TagCategory.ARTIST: ["artist_a"],
                TagCategory.COPYRIGHT: ["series"],
                TagCategory.CHARACTER: ["char"],
                TagCategory.META: ["highres"],
            },
        )

    def test_source_uses_first_url(self) -> None:
        post = GelbooruPost(id=1, source="https://a.example/1 https://b.example/2")

        self.assertEqual(get_gelbooru_source(post), "https://a.example/1")
        self.assertIsNone(get_gelbooru_source(GelbooruPost(id=1, source="")))


if __name__ == "__main__":
    unittest.main()
