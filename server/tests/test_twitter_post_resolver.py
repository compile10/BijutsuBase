"""Tests for resolving Twitter/X post URLs to original-quality media."""

import unittest

import httpx

from sources.twitter.post_resolver import (
    TwitterApiError,
    TwitterPostUnavailableError,
    get_twitter_post_id,
    resolve_twitter_post,
    to_twimg_size_url,
)


def _photo(media_key: str, width: int = 900, height: int = 1200) -> dict:
    return {
        "type": "photo",
        "media_url_https": f"https://pbs.twimg.com/media/{media_key}.jpg",
        "original_info": {"width": width, "height": height},
    }


class GetTwitterPostIdTests(unittest.TestCase):
    def test_extracts_post_id_from_supported_hosts_and_paths(self) -> None:
        urls = [
            "https://x.com/artist/status/1231446342578397184",
            "https://twitter.com/artist/status/1231446342578397184?s=20",
            "https://mobile.twitter.com/artist/status/1231446342578397184/photo/2",
            "https://fxtwitter.com/artist/status/1231446342578397184",
            "https://x.com/i/web/status/1231446342578397184",
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(get_twitter_post_id(url), "1231446342578397184")

    def test_rejects_non_post_urls(self) -> None:
        urls = [
            "https://x.com/artist",
            "https://x.com/artist/likes",
            "https://example.com/artist/status/1231446342578397184",
            "https://pbs.twimg.com/media/ERb57C8WoAISEYi.jpg",
            # Longer than any 64-bit snowflake ID
            "https://x.com/artist/status/" + "9" * 400,
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertIsNone(get_twitter_post_id(url))


class ToTwimgSizeUrlTests(unittest.TestCase):
    def test_rewrites_all_known_forms_to_orig(self) -> None:
        expected = "https://pbs.twimg.com/media/ERb57C8WoAISEYi?format=jpg&name=orig"
        urls = [
            "https://pbs.twimg.com/media/ERb57C8WoAISEYi.jpg",
            "https://pbs.twimg.com/media/ERb57C8WoAISEYi.jpg:large",
            "https://pbs.twimg.com/media/ERb57C8WoAISEYi?format=jpg&name=small",
            "https://pbs.twimg.com/media/ERb57C8WoAISEYi?format=jpg&name=4096x4096",
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(to_twimg_size_url(url, "orig"), expected)

    def test_preserves_format(self) -> None:
        self.assertEqual(
            to_twimg_size_url("https://pbs.twimg.com/media/ABC.png", "orig"),
            "https://pbs.twimg.com/media/ABC?format=png&name=orig",
        )

    def test_leaves_other_hosts_unchanged(self) -> None:
        url = "https://cdn.donmai.us/original/c4/29/image.jpg"

        self.assertEqual(to_twimg_size_url(url, "orig"), url)


class ResolveTwitterPostTests(unittest.IsolatedAsyncioTestCase):
    async def _resolve(self, payload: dict | None, status_code: int = 200):
        def handle_request(request: httpx.Request) -> httpx.Response:
            self.assertEqual(request.url.host, "cdn.syndication.twimg.com")
            self.assertEqual(request.url.params["id"], "1231446342578397184")
            if payload is None:
                return httpx.Response(status_code, text="not found")
            return httpx.Response(status_code, json=payload)

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handle_request)
        ) as client:
            return await resolve_twitter_post(
                "https://twitter.com/someone/status/1231446342578397184/photo/1",
                client,
            )

    async def test_resolves_photos_to_orig_and_video_to_best_mp4(self) -> None:
        post = await self._resolve(
            {
                "__typename": "Tweet",
                "text": "new art",
                "user": {"screen_name": "artist", "name": "Artist"},
                "mediaDetails": [
                    _photo("AAA"),
                    {
                        "type": "video",
                        "media_url_https": "https://pbs.twimg.com/amplify_video_thumb/1/img/BBB.jpg",
                        "original_info": {"width": 1920, "height": 1080},
                        "video_info": {
                            "variants": [
                                {
                                    "content_type": "application/x-mpegURL",
                                    "url": "https://video.twimg.com/pl/x.m3u8",
                                },
                                {
                                    "bitrate": 2176000,
                                    "content_type": "video/mp4",
                                    "url": "https://video.twimg.com/720.mp4",
                                },
                                {
                                    "bitrate": 10368000,
                                    "content_type": "video/mp4",
                                    "url": "https://video.twimg.com/1080.mp4",
                                },
                            ]
                        },
                    },
                    _photo("CCC"),
                ],
            }
        )

        self.assertEqual(post.url, "https://x.com/artist/status/1231446342578397184")
        self.assertEqual(post.author_screen_name, "artist")
        self.assertEqual([media.index for media in post.media], [1, 2, 3])
        self.assertEqual(
            [media.url for media in post.media],
            [
                "https://pbs.twimg.com/media/AAA?format=jpg&name=orig",
                "https://video.twimg.com/1080.mp4",
                "https://pbs.twimg.com/media/CCC?format=jpg&name=orig",
            ],
        )
        self.assertEqual(
            post.media[0].thumbnail_url,
            "https://pbs.twimg.com/media/AAA?format=jpg&name=small",
        )
        self.assertEqual((post.media[1].width, post.media[1].height), (1920, 1080))

    async def test_rejects_post_without_media(self) -> None:
        with self.assertRaisesRegex(TwitterPostUnavailableError, "no downloadable media"):
            await self._resolve(
                {"__typename": "Tweet", "text": "hi", "user": {"screen_name": "a"}}
            )

    async def test_rejects_malformed_media_metadata(self) -> None:
        for media_details in ("oops", ["oops"], {"type": "photo"}):
            with self.subTest(media_details=media_details):
                with self.assertRaisesRegex(TwitterApiError, "invalid media metadata"):
                    await self._resolve(
                        {
                            "__typename": "Tweet",
                            "user": {"screen_name": "a"},
                            "mediaDetails": media_details,
                        }
                    )

    async def test_skips_video_with_malformed_variants(self) -> None:
        post = await self._resolve(
            {
                "__typename": "Tweet",
                "user": {"screen_name": "a"},
                "mediaDetails": [
                    _photo("AAA"),
                    {
                        "type": "video",
                        "media_url_https": "https://pbs.twimg.com/x/BBB.jpg",
                        "video_info": {"variants": ["oops", {"content_type": "video/mp4"}]},
                    },
                ],
            }
        )

        self.assertEqual([media.type for media in post.media], ["photo"])

    async def test_rejects_tombstone(self) -> None:
        with self.assertRaisesRegex(TwitterPostUnavailableError, "age-restricted.*without logging in"):
            await self._resolve({"__typename": "TweetTombstone"})

    async def test_tombstone_includes_twitter_reason(self) -> None:
        reason = "Age-restricted adult content. To view this media, you'll need to log in to X."

        with self.assertRaisesRegex(
            TwitterPostUnavailableError,
            "Post 1231446342578397184 is unavailable: Age-restricted adult content.*without logging in",
        ):
            await self._resolve(
                {"__typename": "TweetTombstone", "tombstone": {"text": {"text": reason}}}
            )

    async def test_rejects_missing_post(self) -> None:
        with self.assertRaisesRegex(TwitterPostUnavailableError, "not found.*protected account"):
            await self._resolve(None, status_code=404)


if __name__ == "__main__":
    unittest.main()
