import asyncio
import io

from fastapi import UploadFile
from minio import Minio
from minio.error import S3Error

from app.core.minio_settings import settings


class MinioClient:
    """Wraps the blocking MinIO SDK; every SDK call runs on a worker thread."""

    def __init__(self):
        self.minio_url = settings.minio_url.replace("http://", "").replace(
            "https://", ""
        )
        self.minio_client = Minio(
            self.minio_url,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
        self.bucket_name = settings.minio_bucket
        # Set after the first successful check; a failure is not remembered
        self.bucket_ready = False

    async def ensure_bucket(self) -> None:
        """Create the bucket if it is missing; raises on a storage error.

        Called on the first upload, not at startup: with placeholder settings the
        client retries for seconds and the app must still start at once.
        """
        if self.bucket_ready:
            return
        if not await asyncio.to_thread(self.minio_client.bucket_exists, self.bucket_name):
            await asyncio.to_thread(self.minio_client.make_bucket, self.bucket_name)
        self.bucket_ready = True

    async def upload_file(self, file: UploadFile, object_name: str) -> str:
        try:
            content = await file.read()
            await asyncio.to_thread(
                self.minio_client.put_object,
                self.bucket_name,
                object_name,
                io.BytesIO(content),
                length=len(content),
            )
            return f"{settings.minio_url}/{self.bucket_name}/{object_name}"
        except S3Error as err:
            return f"Error occurred: {err}"

    async def get_file(self, object_name: str):
        try:
            return await asyncio.to_thread(
                self.minio_client.get_object, self.bucket_name, object_name
            )
        except S3Error as err:
            return f"Error occurred: {err}"

    async def remove_file(self, object_name: str) -> str:
        try:
            await asyncio.to_thread(
                self.minio_client.remove_object, self.bucket_name, object_name
            )
            return f"File '{object_name}' removed successfully"
        except S3Error as err:
            return f"Error occurred: {err}"


minio = MinioClient()
