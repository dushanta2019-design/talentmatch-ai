"""File storage: S3-compatible (MinIO/S3/R2) in production, local disk in dev."""

import uuid
from pathlib import Path

from app.config import get_settings


def _use_local() -> bool:
    s = get_settings()
    return s.dev_mode or s.storage_backend == "local"


def _local_root() -> Path:
    root = Path(get_settings().local_storage_dir)
    root.mkdir(parents=True, exist_ok=True)
    return root


def _client():
    import boto3
    from botocore.config import Config

    s = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=s.s3_endpoint_url,
        aws_access_key_id=s.s3_access_key,
        aws_secret_access_key=s.s3_secret_key,
        region_name=s.s3_region,
        config=Config(signature_version="s3v4"),
    )


def upload_bytes(data: bytes, filename: str, content_type: str, prefix: str) -> str:
    key = f"{prefix}/{uuid.uuid4()}/{filename}"
    if _use_local():
        path = _local_root() / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key
    _client().put_object(
        Bucket=get_settings().s3_bucket, Key=key, Body=data, ContentType=content_type
    )
    return key


def download_bytes(key: str) -> bytes:
    if _use_local():
        return (_local_root() / key).read_bytes()
    obj = _client().get_object(Bucket=get_settings().s3_bucket, Key=key)
    return obj["Body"].read()


def presigned_url(key: str, expires: int = 900) -> str:
    if _use_local():
        return f"file://{(_local_root() / key).resolve()}"
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": get_settings().s3_bucket, "Key": key},
        ExpiresIn=expires,
    )
