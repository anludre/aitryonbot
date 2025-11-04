from __future__ import annotations

import asyncio
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message

from bot.config import get_settings, ensure_data_dirs
from bot.keyboards import main_menu
from bot.flows.prepare_item import router as items_router


settings = get_settings()
ensure_data_dirs(settings)

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
dp = Dispatcher()
dp.include_router(items_router)


@dp.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Примерьте одежду на своих фото. Что делаем?",
        reply_markup=main_menu(),
    )

# Fallback: handle plain "start ..." text without slash
@dp.message(F.text.regexp(r"(?i)^start\b"))
async def cmd_start_fallback(message: Message) -> None:
    await cmd_start(message)


@dp.message(F.text == "Примерить одежду")
async def handle_try_on_entry(message: Message) -> None:
    await message.answer(
        "Загрузите своё фото. Требования — в ‘Гид по фото’.",
    )


@dp.message(F.text == "Гид по фото")
async def handle_photo_guide(message: Message) -> None:
    await message.answer(
        (
            "Чтобы результат был реалистичным:\n"
            "- Лицо и фигура целиком, без сильных теней.\n"
            "- Нейтральный фон, хорошее освещение.\n"
            "- Поза фронтальная или в 3/4, руки не перекрывают торс.\n"
            "- Вещь на фото — ровно расправлена."
        ),
        reply_markup=main_menu(),
    )


@dp.message(F.text == "Мои образы")
async def handle_outfits(message: Message) -> None:
    await message.answer(
        "Тут появятся ваши примерки. Сделаем первую?",
        reply_markup=main_menu(),
    )


@dp.message(F.text == "Тарифы")
async def handle_pricing(message: Message) -> None:
    await message.answer(
        "Баланс: —. 1 примерка ≈ K1 кр. Апскейл ≈ K2 кр.",
        reply_markup=main_menu(),
    )


@dp.message(F.text == "Поддержка")
async def handle_support(message: Message) -> None:
    await message.answer(
        "Напишите вопрос, мы отвечаем в течение нескольких часов. FAQ скоро.",
        reply_markup=main_menu(),
    )


app = FastAPI()


@app.on_event("startup")
async def on_startup() -> None:
    if settings.PUBLIC_BASE_URL:
        webhook_url = f"{settings.PUBLIC_BASE_URL}/telegram/webhook?secret={settings.WEBHOOK_SECRET}"
        await bot.set_webhook(url=webhook_url, secret_token=settings.WEBHOOK_SECRET)


@app.on_event("shutdown")
async def on_shutdown() -> None:
    if settings.PUBLIC_BASE_URL:
        await bot.delete_webhook()


@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/telegram/webhook")
async def telegram_webhook(request: Request) -> JSONResponse:
    token = request.query_params.get("secret")
    if token != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="invalid secret")
    try:
        update = await request.json()
    except Exception as e:  # noqa: PIE786
        raise HTTPException(status_code=400, detail="invalid update") from e

    # Process update in background to respond immediately and avoid Telegram timeouts
    asyncio.create_task(dp.feed_webhook_update(bot=bot, update=update))
    return JSONResponse({"ok": True})


