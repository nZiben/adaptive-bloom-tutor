import boto3, io, json
from .config import settings

def _client():
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
    )

def ensure_bucket():
    s3 = _client()
    try:
        s3.head_bucket(Bucket=settings.s3_bucket)
    except Exception:
        s3.create_bucket(Bucket=settings.s3_bucket)

def put_bytes(key: str, data: bytes, content_type: str):
    _client().put_object(Bucket=settings.s3_bucket, Key=key, Body=data, ContentType=content_type)
    return f"{settings.s3_endpoint_url}/{settings.s3_bucket}/{key}"

def put_json(key: str, obj: dict):
    data = json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8")
    return put_bytes(key, data, "application/json")
