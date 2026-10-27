import httpx
import pytest
from fastapi import HTTPException
from PIL import Image, ImageDraw, ImageFont

from backend.app.services import fetch_url as fetch_module
from backend.app.services.extraction import Section, extract_sections
from backend.app.services.fetch_url import ensure_public_url, fetch_url, make_filename
from backend.tests.conftest import auth_headers

PUBLIC_IP = "93.184.216.34"


def text_image(text: str) -> Image.Image:
    image = Image.new("RGB", (900, 160), "white")
    ImageDraw.Draw(image).text((30, 40), text, fill="black", font=ImageFont.load_default(size=56))
    return image


def test_html_drops_markup_scripts_and_styles(tmp_path):
    path = tmp_path / "page.html"
    path.write_text(
        "<html><head><title>T</title><style>p{color:red}</style>"
        "<script>alert(1)</script></head>"
        "<body><h1>Заголовок</h1><p>Текст <b>страницы</b></p></body></html>",
        encoding="utf-8",
    )

    [section] = extract_sections(path)

    assert section.text.split("\n") == ["T", "Заголовок", "Текст", "страницы"]


def test_markdown_is_read_as_text(tmp_path):
    path = tmp_path / "notes.md"
    path.write_text("# Заметки\n\n- пункт", encoding="utf-8")

    assert extract_sections(path) == [Section("# Заметки\n\n- пункт")]


def test_image_is_recognized_with_ocr(tmp_path):
    path = tmp_path / "scan.png"
    text_image("Invoice 4471").save(path)

    [section] = extract_sections(path)

    assert "Invoice 4471" in section.text


def test_scanned_pdf_page_is_recognized_with_ocr(tmp_path):
    path = tmp_path / "scan.pdf"
    text_image("Scanned page 7").save(path, "PDF", resolution=100)

    [section] = extract_sections(path)

    assert section.page == 1
    assert "Scanned page 7" in section.text


@pytest.mark.parametrize(
    "url",
    [
        "ftp://example.com/file.txt",
        "http://127.0.0.1/",
        "http://localhost:9000/documents",
        "http://10.0.0.5/",
        "http://169.254.169.254/latest/meta-data/",
        "http://minio:9000/",
        "http://db:5432/",
    ],
)
async def test_internal_and_non_http_links_are_rejected(url):
    with pytest.raises(HTTPException) as error:
        await ensure_public_url(url)

    assert error.value.status_code == 400


async def test_public_ip_is_allowed():
    await ensure_public_url(f"http://{PUBLIC_IP}/page")


@pytest.mark.parametrize(
    ("url", "content_type", "filename"),
    [
        ("https://example.com/files/report.pdf", "application/pdf", "report.pdf"),
        ("https://example.com/wiki/Ветер", "text/html", "Ветер.html"),
        ("https://example.com/", "text/html", "example.com.html"),
        ("https://example.com/a b.txt", "text/plain", "a_b.txt"),
    ],
)
def test_make_filename(url, content_type, filename):
    assert make_filename(url, content_type) == filename


def mock_network(monkeypatch, handler):
    real_client = httpx.AsyncClient

    monkeypatch.setattr(
        fetch_module.httpx,
        "AsyncClient",
        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs),
    )


async def test_fetch_follows_redirects(monkeypatch):
    def handler(request):
        if request.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new/page.html"})
        return httpx.Response(200, html="<p>Привет</p>")

    mock_network(monkeypatch, handler)

    fetched = await fetch_url(f"http://{PUBLIC_IP}/old")

    assert fetched.filename == "page.html"
    assert fetched.content_type == "text/html"
    assert fetched.file.read() == "<p>Привет</p>".encode()


async def test_fetch_blocks_redirect_to_internal_address(monkeypatch):
    requested = []

    def handler(request):
        requested.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://127.0.0.1:9000/documents"})

    mock_network(monkeypatch, handler)

    with pytest.raises(HTTPException) as error:
        await fetch_url(f"http://{PUBLIC_IP}/redirect")

    assert error.value.status_code == 400
    assert requested == [f"http://{PUBLIC_IP}/redirect"]


async def test_fetch_rejects_unsupported_content_type(monkeypatch):
    mock_network(monkeypatch, lambda request: httpx.Response(200, content=b"x", headers={"content-type": "application/zip"}))

    with pytest.raises(HTTPException) as error:
        await fetch_url(f"http://{PUBLIC_IP}/archive")

    assert error.value.status_code == 415


async def test_upload_from_url(client, storage, queued, monkeypatch):
    headers = await auth_headers(client)
    mock_network(monkeypatch, lambda request: httpx.Response(200, html="<p>Документ по ссылке</p>"))

    response = await client.post(
        "/documents/url",
        headers=headers,
        json={"url": f"http://{PUBLIC_IP}/article"},
    )

    document = response.json()
    assert response.status_code == 200
    assert document["filename"] == "article.html"
    assert queued == [document["id"]]
    assert storage.files[f"documents/{document['id']}/article.html"] == "<p>Документ по ссылке</p>".encode()


async def test_upload_from_internal_url_is_rejected(client, queued):
    headers = await auth_headers(client)

    response = await client.post(
        "/documents/url",
        headers=headers,
        json={"url": "http://minio:9000/documents/1/secret.txt"},
    )

    assert response.status_code == 400
    assert queued == []
