from __future__ import annotations

import os

from celery import Celery

from bot.config import get_settings


settings = get_settings()

celery_app = Celery(
    "ai_fashion_bot",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.task_queues = ("models", "items", "tryon")


@celery_app.task(name="flows.prepare_item", queue="items")
def prepare_item_task(user_id: str, item_id: str) -> dict:
    # TODO: background removal, enhancement, alignment
    return {"status": "ok", "user_id": user_id, "item_id": item_id}


@celery_app.task(name="flows.try_on", queue="tryon")
def try_on_task(user_id: str, item_id: str) -> dict:
    # TODO: call Segmind Try-On Diffusion
    return {"status": "queued", "user_id": user_id, "item_id": item_id}


