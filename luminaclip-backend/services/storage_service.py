"""
Storage Service — S3/R2 ile dosya yönetimi
"""
import boto3
from botocore.exceptions import ClientError
from core.config import settings
import os

s3_client = boto3.client(
    "s3",
    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
    region_name=settings.AWS_REGION,
)

async def upload_clip(local_path: str, clip_id: str) -> str:
    """Klibi S3'e yükler, URL döndürür."""
    s3_key = f"clips/{clip_id}.mp4"
    try:
        s3_client.upload_file(
            local_path,
            settings.AWS_BUCKET_NAME,
            s3_key,
            ExtraArgs={"ContentType": "video/mp4", "ACL": "public-read"}
        )
        return f"https://{settings.AWS_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
    except ClientError as e:
        raise Exception(f"S3 upload failed: {e}")

async def get_presigned_url(clip_id: str, expires: int = 3600) -> str:
    """İndirme için geçici URL üretir."""
    return s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.AWS_BUCKET_NAME, "Key": f"clips/{clip_id}.mp4"},
        ExpiresIn=expires
    )
