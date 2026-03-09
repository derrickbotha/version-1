
import logging
import uuid

import boto3
import botocore.exceptions
from fastapi import HTTPException, status

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS: set[str] = {".pdf", ".docx", ".xlsx", ".txt", ".zip"}
ALLOWED_MIME_TYPES: set[str] = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "text/plain",
    "application/zip",
    "application/x-zip-compressed",
}
MAX_SIZE_BYTES: int = settings.max_upload_mb * 1024 * 1024


def get_s3_client():  # type: ignore[return]
    """Return a configured boto3 S3 client using application settings."""
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


def validate_file(filename: str, content_type: str, size: int) -> None:
    """
    Validate file extension, MIME type, and size.

    Raises:
        HTTPException 400 — if the extension is not allowed, the MIME type is
        not allowed, or the file exceeds the size limit.
    """
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File extension '{ext}' is not allowed. "
                f"Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            ),
        )

    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"MIME type '{content_type}' is not allowed. "
                f"Allowed types: {', '.join(sorted(ALLOWED_MIME_TYPES))}"
            ),
        )

    if size > MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File size {size} bytes exceeds the maximum allowed size of "
                f"{settings.max_upload_mb} MB ({MAX_SIZE_BYTES} bytes)."
            ),
        )


def upload_file(
    file_content: bytes,
    filename: str,
    content_type: str,
    folder: str = "uploads",
) -> str:
    """
    Upload *file_content* to S3 and return the S3 object key.

    The key is generated as ``{folder}/{uuid4}/{filename}`` to avoid
    collisions.  A signed URL can be generated separately via
    :func:`generate_signed_url`.

    Raises:
        HTTPException 500 — if the S3 upload fails.
    """
    unique_key = f"{folder}/{uuid.uuid4()}/{filename}"
    try:
        client = get_s3_client()
        client.put_object(
            Bucket=settings.aws_bucket_name,
            Key=unique_key,
            Body=file_content,
            ContentType=content_type,
        )
        logger.info("Uploaded file to S3: %s", unique_key)
        return unique_key
    except botocore.exceptions.BotoCoreError as exc:
        logger.exception("S3 upload failed for key %s: %s", unique_key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed. Please try again later.",
        ) from exc
    except botocore.exceptions.ClientError as exc:
        logger.exception("S3 client error for key %s: %s", unique_key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="File upload failed. Please try again later.",
        ) from exc


def generate_signed_url(s3_key: str, expires_in: int = 3600) -> str:
    """
    Generate a pre-signed GET URL for *s3_key* valid for *expires_in* seconds.

    Raises:
        HTTPException 500 — if the pre-signed URL cannot be generated.
    """
    try:
        client = get_s3_client()
        url: str = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.aws_bucket_name, "Key": s3_key},
            ExpiresIn=expires_in,
        )
        return url
    except botocore.exceptions.BotoCoreError as exc:
        logger.exception("Failed to generate signed URL for %s: %s", s3_key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate file download URL.",
        ) from exc
    except botocore.exceptions.ClientError as exc:
        logger.exception("S3 client error generating signed URL for %s: %s", s3_key, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate file download URL.",
        ) from exc


def delete_file(s3_key: str) -> bool:
    """
    Delete the object at *s3_key* from S3.

    Returns:
        True  — if the deletion succeeded.
        False — if the deletion failed (error is logged but not re-raised).
    """
    try:
        client = get_s3_client()
        client.delete_object(Bucket=settings.aws_bucket_name, Key=s3_key)
        logger.info("Deleted S3 object: %s", s3_key)
        return True
    except (botocore.exceptions.BotoCoreError, botocore.exceptions.ClientError) as exc:
        logger.exception("Failed to delete S3 object %s: %s", s3_key, exc)
        return False
