from __future__ import annotations

import hashlib
import secrets
from pathlib import PurePosixPath

from app.config import settings


class StorageNotConfigured(RuntimeError):
    pass


ALLOWED_TYPES = {"application/pdf", "image/jpeg", "image/png"}
MAX_DOCUMENT_BYTES = 15 * 1024 * 1024


def validate_document(*, filename: str, content_type: str, size_bytes: int) -> None:
    extension = PurePosixPath(filename).suffix.lower()
    if content_type not in ALLOWED_TYPES or extension not in {".pdf", ".jpg", ".jpeg", ".png"}:
        raise ValueError("Unsupported verification document type")
    if size_bytes <= 0 or size_bytes > MAX_DOCUMENT_BYTES:
        raise ValueError("Verification document exceeds the permitted size")


def private_object_key(*, tenant_id: str, application_id: str, filename: str) -> str:
    safe_name = PurePosixPath(filename).name.replace(" ", "_")[:120]
    return f"private/{tenant_id}/{application_id}/{secrets.token_urlsafe(18)}-{safe_name}"


def checksum_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _client():
    if settings.storage_provider != "S3" or not settings.storage_bucket or not settings.storage_access_key or not settings.storage_secret_key:
        raise StorageNotConfigured("Private object storage is not configured")
    import boto3
    return boto3.client("s3", region_name=settings.storage_region, endpoint_url=settings.storage_endpoint, aws_access_key_id=settings.storage_access_key, aws_secret_access_key=settings.storage_secret_key)


def signed_upload_url(*, object_key: str, content_type: str) -> str:
    return _client().generate_presigned_url("put_object", Params={"Bucket": settings.storage_bucket, "Key": object_key, "ContentType": content_type}, ExpiresIn=settings.signed_url_ttl_seconds)


def signed_download_url(*, object_key: str) -> str:
    return _client().generate_presigned_url("get_object", Params={"Bucket": settings.storage_bucket, "Key": object_key}, ExpiresIn=settings.signed_url_ttl_seconds)
