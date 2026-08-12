# RAG Site

Веб-приложение для загрузки документов и поиска ответов по их содержимому. Бэкенд обрабатывает файлы в фоне, сохраняет их в S3-совместимое хранилище, создаёт эмбеддинги через OpenRouter и использует PostgreSQL с расширением pgvector для поиска.

## Стек

- **Frontend:** Vue 3, TypeScript, Vite, Tailwind CSS, Socket.IO client
- **Backend:** FastAPI, SQLAlchemy, Celery, Socket.IO
- **Данные и очереди:** PostgreSQL + pgvector, Redis, RabbitMQ, MinIO
- **LLM и эмбеддинги:** OpenRouter
- **Контейнеризация:** Docker Compose

## Сервисы

| Сервис | Адрес с хоста | Назначение |
| --- | --- | --- |
| Frontend | http://localhost:5173 | Интерфейс Vue и Vite-прокси для API |
| API | http://localhost:8000 | FastAPI и Socket.IO |
| API docs | http://localhost:8000/docs | Swagger UI |
| PostgreSQL | `localhost:5432` | База данных и pgvector |
| RabbitMQ | http://localhost:15672 | Панель управления очередями |
| MinIO API | http://localhost:9000 | S3-совместимое файловое хранилище |
| MinIO Console | http://localhost:9001 | Панель MinIO |

## Быстрый запуск

### 1. Подготовьте переменные окружения

Создайте в корне проекта файл `.env`. Пример минимальной конфигурации:

```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/rag
RABBITMQ_URL=amqp://guest:guest@rabbitmq:5672//
REDIS_URL=redis://redis:6379/0

S3_ENDPOINT_URL=http://minio:9000
S3_ACCESS_KEY=minio
S3_SECRET_KEY=minio123
S3_BUCKET=documents

OPENROUTER_API_KEY=ваш_ключ_OpenRouter
OPENROUTER_LLM_MODEL=google/gemini-2.5-flash-lite
OPENROUTER_EMBEDDING_MODEL=openai/text-embedding-3-small
OPENROUTER_EMBEDDING_MODEL_DIMENSIONS=1536
MAX_DISTANCE=0.7

JWT_SECRET_KEY=длинный_случайный_секрет
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30
```

`.env` уже исключён из Git — не добавляйте в репозиторий реальные ключи.

### 2. Запустите приложение

```bash
docker compose up --build
```

Для запуска в фоне:

```bash
docker compose up -d --build
```

После старта откройте http://localhost:5173. Фронтенд перезапускается при изменениях в `frontend/`, а API — при изменениях в `backend/`.

### 3. Остановка

```bash
docker compose down
```

Данные PostgreSQL, MinIO, загруженные файлы и зависимости фронтенда лежат в Docker volumes и сохраняются между перезапусками. Чтобы удалить также данные, используйте:

```bash
docker compose down -v
```

## Архитектура

```text
Браузер → frontend:5173 → /api → app:8000
                                ├─ PostgreSQL + pgvector
                                ├─ RabbitMQ → Celery worker
                                ├─ Redis
                                ├─ MinIO
                                └─ OpenRouter
```

Фронтенд проксирует запросы `/api` к контейнеру `app`; Socket.IO подключается к API на порту `8000`. Обработка загруженных документов выполняется фоновым Celery-воркером.

## Основные API-маршруты

Базовый префикс API: `/api/v1`.

| Метод | Маршрут | Назначение |
| --- | --- | --- |
| `GET` | `/healthz` | Проверка доступности API |
| `POST` | `/auth/register` | Регистрация пользователя |
| `POST` | `/auth/login` | Авторизация |
| `GET` | `/auth/me` | Текущий пользователь |
| `POST` | `/auth/refresh` | Обновление токенов |
| `POST` | `/documents` | Загрузка документа |
| `GET` | `/documents` | Список документов пользователя |
| `GET`, `DELETE` | `/documents/{document_id}` | Просмотр или удаление документа |
| `POST` | `/search` | Поиск по документам |
| `POST` | `/ask` | Вопрос к документам (RAG) |

Для защищённых маршрутов передавайте access token в заголовке:

```http
Authorization: Bearer <access_token>
```

## Полезные команды

```bash
# Статус контейнеров
docker compose ps

# Логи всех сервисов
docker compose logs -f

# Логи конкретного сервиса
docker compose logs -f app
docker compose logs -f worker
docker compose logs -f frontend

# Пересобрать только фронтенд
docker compose build frontend

# Перезапустить только фронтенд
docker compose up -d frontend
```

## Структура проекта

```text
backend/                 FastAPI-приложение, Celery и миграции Alembic
  app/api/               REST API
  app/services/          бизнес-логика, RAG и хранилище
  app/tasks/             фоновые задачи Celery
frontend/                Vue-приложение
docker-compose.yaml      конфигурация локального окружения
```

## Локальная разработка без Docker

Для фронтенда:

```bash
cd frontend
npm install
npm run dev
```

Для полноценной работы API локально всё равно должны быть доступны PostgreSQL, RabbitMQ, Redis и MinIO; удобнее запускать их через Docker Compose.
