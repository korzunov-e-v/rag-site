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
            aws_secret_access_key=settings.s3_secret_key,
        )

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
