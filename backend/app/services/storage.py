from io import BytesIO
from typing import BinaryIO

import boto3

from backend.app.settings import settings
from botocore.exceptions import BotoCoreError, ClientError

from backend.app.exceptions import RetryableError

class S3Storage:
    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key.get_secret_value(),
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=settings.s3_bucket)
        except ClientError as error:
            if error.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
                raise

            self.client.create_bucket(Bucket=settings.s3_bucket)

    def upload(self, file, key: str) -> None:
        self.client.upload_fileobj(
            file,
            settings.s3_bucket,
            key,
        )

    def delete(self, key: str) -> None:
        self.client.delete_object(
            Bucket=settings.s3_bucket,
            Key=key,
        )

    def download(self, key: str) -> BytesIO:
        file = BytesIO()

        try:
            self.client.download_fileobj(
                settings.s3_bucket,
                key,
                file,
            )
        except (BotoCoreError, ClientError) as error:
            raise RetryableError("Failed to download file from storage") from error

        file.seek(0)
        return file

s3_storage = S3Storage()
