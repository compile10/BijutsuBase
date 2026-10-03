from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from api.serializers.file import FileResponse

MAX_BATCH_URL_UPLOADS = 20
# Matches the files.source column
MAX_SOURCE_LENGTH = 2048


class UrlUploadRequest(BaseModel):
    url: HttpUrl
    # Recorded as the file's source; Danbooru enrichment overrides it on a hit
    source: str | None = Field(default=None, max_length=MAX_SOURCE_LENGTH)


class BatchUrlUploadItem(BaseModel):
    """Loosely typed so a bad item fails on its own instead of rejecting the batch."""

    url: str
    source: str | None = None


class BatchUrlUploadRequest(BaseModel):
    items: list[BatchUrlUploadItem] = Field(min_length=1, max_length=MAX_BATCH_URL_UPLOADS)


class BatchUrlUploadResult(BaseModel):
    url: str
    status: Literal["uploaded", "duplicate", "failed"]
    # Set for uploads and duplicates
    sha256_hash: str | None = None
    # Set for uploads only
    file: FileResponse | None = None
    # Set for failures only
    error: str | None = None


class BatchUrlUploadResponse(BaseModel):
    results: list[BatchUrlUploadResult]
