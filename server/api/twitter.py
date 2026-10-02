"""Twitter/X router for BijutsuBase API."""

import httpx
from fastapi import APIRouter, Depends, HTTPException, status

from api.serializers.twitter import TwitterPost, TwitterResolveRequest
from auth.users import current_active_user
from models.user import User
from sources.twitter.post_resolver import (
    TwitterApiError,
    TwitterPostUnavailableError,
    get_twitter_post_id,
    resolve_twitter_post,
)

router = APIRouter(prefix="/twitter", tags=["twitter"])


@router.post("/resolve", response_model=TwitterPost)
async def resolve_post(
    payload: TwitterResolveRequest,
    user: User = Depends(current_active_user),
) -> TwitterPost:
    """
    Resolve a Twitter/X post URL to its media, with original-quality download
    URLs and small thumbnails for selection.
    """
    source_url = str(payload.url)
    if get_twitter_post_id(source_url) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL is not a Twitter/X post",
        )

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            headers={"User-Agent": "BijutsuBase/0.1.0"},
        ) as client:
            return await resolve_twitter_post(source_url, client)
    except TwitterPostUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except (TwitterApiError, httpx.HTTPError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to resolve post: {error}",
        ) from error
