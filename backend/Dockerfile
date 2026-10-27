FROM python:3.14-slim

WORKDIR /app
# Не писать __pycache__ в примонтированный с хоста код (он создавался бы от root).
ENV PYTHONDONTWRITEBYTECODE=1
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libmagic1 \
        tesseract-ocr \
        tesseract-ocr-rus \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml uv.lock ./

RUN pip install uv \
    && uv sync --frozen

COPY alembic.ini ./
COPY . ./backend
