import asyncio
import ipaddress
import re
import socket
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from urllib.parse import unquote, urljoin, urlsplit

import httpx
from fastapi import HTTPException
from starlette import status

from backend.app.services.save import ALLOWED_EXTENSIONS

MAX_URL_FILE_SIZE = 50 * 1024 * 1024
MAX_REDIRECTS = 5
TIMEOUT_SECONDS = 20

EXTENSIONS_BY_CONTENT_TYPE = {
    "text/html": ".html",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}


@dataclass
class FetchedFile:
    file: BytesIO
    filename: str
    content_type: str
    size: int


def bad_url(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


async def ensure_public_url(url: str) -> None:
    """Защита от SSRF: сервер не должен ходить по ссылкам во внутреннюю сеть
    (MinIO, Postgres, метаданные облака, localhost).

    Проверка не закрывает DNS rebinding (httpx резолвит имя заново при
    подключении); для продакшена стоит ходить наружу через egress-прокси.
    """
    parts = urlsplit(url)

    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise bad_url("Only http and https links are supported")

    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            parts.hostname,
            parts.port or (443 if parts.scheme == "https" else 80),
            type=socket.SOCK_STREAM,
        )
    except socket.gaierror:
        raise bad_url("Could not resolve the link host")

    for *_, sockaddr in addresses:
        if not ipaddress.ip_address(sockaddr[0]).is_global:
            raise bad_url("Links to internal addresses are not allowed")


def make_filename(url: str, content_type: str) -> str:
    parts = urlsplit(url)
    name = unquote(PurePosixPath(parts.path).name)
    extension = PurePosixPath(name).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        extension = EXTENSIONS_BY_CONTENT_TYPE[content_type]
        stem = PurePosixPath(name).stem or parts.hostname
        name = f"{stem}{extension}"

    name = re.sub(r"[^\w.\-]+", "_", name)
    return name[-255:]


async def fetch_url(url: str) -> FetchedFile:
    async with httpx.AsyncClient(
        follow_redirects=False,
        timeout=TIMEOUT_SECONDS,
        headers={"User-Agent": "rag-site/1.0"},
    ) as client:
        # Редиректы обходим вручную: каждый адрес тоже нужно проверить.
        for _ in range(MAX_REDIRECTS + 1):
            await ensure_public_url(url)

            try:
                async with client.stream("GET", url) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers["location"])
                        continue

                    if response.status_code != 200:
                        raise bad_url(f"The link returned HTTP {response.status_code}")

                    content_type = (
                        response.headers.get("content-type", "")
                        .split(";")[0]
                        .strip()
                        .lower()
                    )
                    if content_type not in EXTENSIONS_BY_CONTENT_TYPE:
                        raise HTTPException(
                            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                            detail=f"Unsupported content type: {content_type or 'unknown'}",
                        )

                    file = BytesIO()
                    async for data in response.aiter_bytes():
                        file.write(data)
                        if file.tell() > MAX_URL_FILE_SIZE:
                            raise HTTPException(
                                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                                detail="Linked file must not exceed 50 MB",
                            )

            except httpx.HTTPError:
                raise bad_url("Could not download the link")

            size = file.tell()
            file.seek(0)

            return FetchedFile(
                file=file,
                filename=make_filename(url, content_type),
                content_type=content_type,
                size=size,
            )

    raise bad_url("Too many redirects")
