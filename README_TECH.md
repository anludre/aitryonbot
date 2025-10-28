### AI Fashion Try-On Bot — Техническое руководство

Это дополнение к основному README. Здесь закреплены стек, архитектурные договорённости, схемы данных (pydantic + JSON Schema), надёжность/очередь задач, логирование/трассировка, FSM бота, reproducibility и тестирование.

---

## Стек (принято)

- **Telegram Bot**: aiogram (v3, async FSM)
- **Backend API**: FastAPI (webhook бота + тех.эндпоинты)
- **Очередь задач**: Celery + Redis (broker + result backend)
- **HTTP-клиент**: httpx + tenacity (ретраи с backoff)
- **Валидация/схемы**: pydantic v2 (+ pydantic-settings)
- **Логирование**: structlog (JSON‑формат) + опц. OpenTelemetry (OTLP)
- **Тесты**: pytest, pytest-asyncio, respx (mock httpx)
- **Python**: 3.12

---

## Архитектура (высокоуровнево)

- FastAPI сервис поднимает:
  - webhook `POST /telegram/webhook` (aiogram в режиме webhook)
  - тех.эндпоинты: `/healthz`, `/jobs/{job_id}` (статус)
- Долгие операции уходят в Celery воркеры: `flows.create_model`, `flows.prepare_item`, `flows.try_on`, `flows.upscale`.
- Redis используется как `broker` и `result backend`.
- Хранилище файлов по умолчанию — локальный `DATA_DIR` (S3/GDrive — адаптер позже).

Очереди Celery (пример):
- `models` — генерация поз/моделей
- `items` — подготовка вещей и измерения
- `tryon` — примерка и апскейл

---

## Схемы данных: измерения и метаданные вещей

### Pydantic модели

```python
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ImageRole(str, Enum):
    source = "source"
    background_removed = "background_removed"
    enhanced = "enhanced"
    aligned = "aligned"
    depth_map = "depth_map"


class BoundingBox(BaseModel):
    x: float = Field(ge=0, le=1, description="left, normalized [0..1]")
    y: float = Field(ge=0, le=1, description="top, normalized [0..1]")
    width: float = Field(ge=0, le=1)
    height: float = Field(ge=0, le=1)


class ImageRef(BaseModel):
    id: str = Field(description="uuid4")
    path: str = Field(description="relative path inside DATA_DIR or s3 uri")
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    mime_type: str = Field(pattern="^image/", description="e.g. image/png")
    checksum_sha256: str = Field(min_length=64, max_length=64)
    role: ImageRole = ImageRole.source
    has_ruler: bool = False
    ruler_length_cm: Optional[float] = Field(default=None, gt=0)
    ruler_bbox: Optional[BoundingBox] = None
    exif_removed: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GarmentMeasurements(BaseModel):
    chest_cm: Optional[float] = Field(default=None, gt=0)
    waist_cm: Optional[float] = Field(default=None, gt=0)
    hips_cm: Optional[float] = Field(default=None, gt=0)
    length_cm: Optional[float] = Field(default=None, gt=0)
    sleeve_cm: Optional[float] = Field(default=None, gt=0)
    shoulder_cm: Optional[float] = Field(default=None, gt=0)
    inseam_cm: Optional[float] = Field(default=None, gt=0)
    scale_ppm: Optional[float] = Field(default=None, gt=0, description="pixels per millimeter")


class ItemMetadata(BaseModel):
    item_id: str
    user_id: str
    category: str = Field(description="e.g. tshirt, hoodie, pants, dress")
    size_system: Optional[str] = Field(default="INT", description="INT|EU|US|RU ...")
    measurements: GarmentMeasurements
    source_images: List[ImageRef]
    processed_images: List[ImageRef] = []
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

### Пример JSON (ItemMetadata)

```json
{
  "item_id": "b7e4a8b8-0f1d-4b77-8a8c-1a1a8a1a8a1a",
  "user_id": "123456",
  "category": "tshirt",
  "size_system": "INT",
  "measurements": {
    "chest_cm": 52.0,
    "length_cm": 72.0,
    "scale_ppm": 3.78
  },
  "source_images": [
    {
      "id": "2a7c1e6f-1b3a-4d0d-9d14-a2d6c7c70f9f",
      "path": "items/123/abc/source_1.png",
      "width": 2048,
      "height": 2048,
      "mime_type": "image/png",
      "checksum_sha256": "4c9a1a7c0b8e0f9c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c",
      "role": "source",
      "has_ruler": true,
      "ruler_length_cm": 10.0,
      "ruler_bbox": { "x": 0.12, "y": 0.82, "width": 0.2, "height": 0.05 },
      "exif_removed": true,
      "created_at": "2025-01-01T12:00:00Z"
    }
  ],
  "processed_images": [
    {
      "id": "0e8f1b2c-3d4e-5f60-7a8b-9c0d1e2f3a4b",
      "path": "items/123/abc/background_removed.png",
      "width": 2048,
      "height": 2048,
      "mime_type": "image/png",
      "checksum_sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "role": "background_removed",
      "exif_removed": true,
      "created_at": "2025-01-01T12:01:00Z"
    }
  ],
  "notes": null,
  "created_at": "2025-01-01T12:00:00Z",
  "updated_at": "2025-01-01T12:05:00Z"
}
```

### JSON Schema (GarmentMeasurements)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/GarmentMeasurements.json",
  "title": "GarmentMeasurements",
  "type": "object",
  "properties": {
    "chest_cm": { "type": "number", "exclusiveMinimum": 0 },
    "waist_cm": { "type": "number", "exclusiveMinimum": 0 },
    "hips_cm": { "type": "number", "exclusiveMinimum": 0 },
    "length_cm": { "type": "number", "exclusiveMinimum": 0 },
    "sleeve_cm": { "type": "number", "exclusiveMinimum": 0 },
    "shoulder_cm": { "type": "number", "exclusiveMinimum": 0 },
    "inseam_cm": { "type": "number", "exclusiveMinimum": 0 },
    "scale_ppm": { "type": "number", "exclusiveMinimum": 0, "description": "pixels per millimeter" }
  },
  "additionalProperties": false
}
```

### JSON Schema (ItemMetadata)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/ItemMetadata.json",
  "title": "ItemMetadata",
  "type": "object",
  "required": ["item_id", "user_id", "category", "measurements", "source_images"],
  "properties": {
    "item_id": { "type": "string" },
    "user_id": { "type": "string" },
    "category": { "type": "string" },
    "size_system": { "type": "string" },
    "measurements": { "$ref": "GarmentMeasurements.json" },
    "source_images": {
      "type": "array",
      "items": { "$ref": "#/$defs/ImageRef" },
      "minItems": 1
    },
    "processed_images": {
      "type": "array",
      "items": { "$ref": "#/$defs/ImageRef" }
    },
    "notes": { "type": ["string", "null"] },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" }
  },
  "$defs": {
    "BoundingBox": {
      "type": "object",
      "properties": {
        "x": { "type": "number", "minimum": 0, "maximum": 1 },
        "y": { "type": "number", "minimum": 0, "maximum": 1 },
        "width": { "type": "number", "minimum": 0, "maximum": 1 },
        "height": { "type": "number", "minimum": 0, "maximum": 1 }
      },
      "required": ["x", "y", "width", "height"],
      "additionalProperties": false
    },
    "ImageRef": {
      "type": "object",
      "properties": {
        "id": { "type": "string" },
        "path": { "type": "string" },
        "width": { "type": "integer", "minimum": 1 },
        "height": { "type": "integer", "minimum": 1 },
        "mime_type": { "type": "string", "pattern": "^image/" },
        "checksum_sha256": { "type": "string", "minLength": 64, "maxLength": 64 },
        "role": { "type": "string", "enum": ["source", "background_removed", "enhanced", "aligned", "depth_map"] },
        "has_ruler": { "type": "boolean" },
        "ruler_length_cm": { "type": ["number", "null"], "exclusiveMinimum": 0 },
        "ruler_bbox": { "$ref": "#/$defs/BoundingBox" },
        "exif_removed": { "type": "boolean" },
        "created_at": { "type": "string", "format": "date-time" }
      },
      "required": ["id", "path", "width", "height", "mime_type", "checksum_sha256", "role", "exif_removed", "created_at"],
      "additionalProperties": false
    }
  },
  "additionalProperties": false
}
```

---

## Надёжность и очередь задач

- Идемпотентность по ключу `idempotency_key = f"{user_id}:{item_id}:{flow}"`.
- Ретраи: `tenacity` (клиент Segmind) и `Celery autoretry_for`, backoff экспоненциальный, `max_retries=5`.
- Статусы задач: `queued → running → done | failed`.
- Таймауты: HTTP 60–120s; общая длительность задачи — через `soft_time_limit`/`time_limit` Celery.
- Кэш по входному хешу (фон, depth/pose, апскейл) для снижения стоимости.

Очереди Celery (рекомендации):
- `models` (конкурентность 1–2), `items` (2–4), `tryon` (1–2). Rate limiting по API Segmind.

---

## Логирование и трассировка

- Формат: JSON‑логи через `structlog`.
- Обязательные поля контекста: `request_id`, `job_id`, `user_id`, `flow`, `step`, `latency_ms`, `cost_usd` (если доступно).
- Корреляция: `request_id = telegram_update_id`; `job_id` пробрасывается от API до воркера.
- Трассировка (опц.): OpenTelemetry OTLP exporter (`OTEL_EXPORTER_OTLP_ENDPOINT`).

Пример событий:
- `flow_start`, `step_start`, `step_finish` (время и ресурсы), `flow_finish`.

---

## UX бота и FSM

Сценарий 1: Создание модели
- States: `choose_gender` → `generate_poses` → `preview` → `done`

Сценарий 2: Подготовка вещи
- States: `collect_photos` → `detect_scale` → `enhance_align` → `measurements_json` → `confirm`

Сценарий 3: Примерка
- States: `select_model` → `select_item` → `generate_tryon` → `upscale` → `deliver`

Общие элементы:
- Команды: `/start`, `/cancel`, `/help`.
- Проверки: наличие фото с рулеткой для измерений; подсказки при ошибках.
- Прогресс: сообщения с ссылкой на `job status` и итоговые файлы.

---

## Reproducibility и зависимости

- Версии зависимостей закреплены в `requirements.txt` (пины).
- Конфиг через `.env`/переменные среды и `pydantic-settings`.
- Pre-commit (black/ruff/isort), Makefile цели: `dev`, `lint`, `fmt`, `test`.

---

## Тестирование

- Юнит‑тесты утилит (rembg/size_detector) на фиксированных изображениях.
- Контракт‑тесты клиента Segmind (respx + зафиксированные JSON‑ответы).
- Смоук e2e: упрощённый прогон "подготовка вещи → примерка" на маленьких фикстурах.

---

## Приложение: Технические детали из README

### Стек и архитектура (таблица)

| Компонент | Описание |
|------------|-----------|
| **Frontend** | Telegram Bot API (через `aiogram` v3, FSM) |
| **Backend** | FastAPI (webhook бота + тех.эндпоинты) |
| **Очередь** | Celery + Redis (broker + result backend) |
| **AI-интеграции** | Segmind API + локальные модели |
| **Хранение данных** | Google Drive / S3 / локальные директории |
| **Формат данных** | PNG для изображений, JSON для метаданных и размеров |
| **Локальные модули** | `rembg`, `segment-anything`, `opencv-python` |

### Структура проекта (план)
```
ai-fashion-bot/
├── README.md
├── README_TECH.md
├── bot/
│   ├── main.py
│   ├── flows/
│   │   ├── create_model.py
│   │   ├── prepare_item.py
│   │   ├── try_on.py
│   ├── services/
│   │   ├── segmind.py
│   │   ├── rembg.py
│   │   ├── sam.py
│   │   └── opencv.py
│   ├── storage/
│   ├── types/
│   └── config.py
├── data/
│   ├── models/
│   ├── items/
│   └── outfits/
├── requirements.txt
├── .env.example
├── .pre-commit-config.yaml
└── Makefile
```

### Переменные окружения (.env)
См. файл `.env.example`. Ключевые:
- `TELEGRAM_BOT_TOKEN`, `SEGMIND_API_KEY`, `DATA_DIR`
- `REDIS_URL`/`CELERY_*` (очереди)
- `PUBLIC_BASE_URL`, `WEBHOOK_SECRET` (webhook)
- `OTEL_*` (трассировка, опционально)

### Пример requirements.txt
```
aiogram==3.13.1
fastapi==0.115.2
uvicorn[standard]==0.31.1
pydantic==2.9.2
pydantic-settings==2.5.2
celery==5.4.0
redis==5.1.1
httpx==0.27.2
tenacity==8.5.0
structlog==24.4.0
python-dotenv==1.0.1
rembg==2.0.56
opencv-python==4.10.0.84
numpy==2.1.2
Pillow==10.4.0
pytest==8.3.3
pytest-asyncio==0.24.0
respx==0.21.1
```


