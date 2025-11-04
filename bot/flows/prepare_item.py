from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InputFile

from bot.keyboards import items_empty_keyboard, items_list_keyboard, main_menu
from bot.storage.files import list_user_items, save_item_photo


router = Router(name=__name__)


class ItemAddStates(StatesGroup):
    waiting_for_item_photo = State()


@router.message(F.text == "Мои вещи")
async def handle_my_items(message: Message) -> None:
    user_id = str(message.from_user.id)
    items = list_user_items(user_id)
    if not items:
        await message.answer(
            "Пока нет вещей. Добавьте первую — так примерки будут быстрее.",
            reply_markup=items_empty_keyboard(),
        )
        return

    rows = [(c.item_id, c.title) for c in items]
    await message.answer("Ваши вещи:", reply_markup=items_list_keyboard(rows))


@router.callback_query(F.data == "items:add")
async def items_add_clicked(cb: CallbackQuery, state: FSMContext) -> None:
    await cb.answer()
    await state.set_state(ItemAddStates.waiting_for_item_photo)
    await cb.message.answer(
        "Загрузите фото вещи на однотонном фоне. Разверните ровно.",
    )


@router.message(ItemAddStates.waiting_for_item_photo, F.photo)
async def receive_item_photo(message: Message, state: FSMContext) -> None:
    user_id = str(message.from_user.id)
    # get largest photo size
    photo = message.photo[-1]
    file = await message.bot.get_file(photo.file_id)
    file_bytes = await message.bot.download_file(file.file_path)
    content = file_bytes.read()

    item_id = save_item_photo(user_id=user_id, photo_bytes=content)
    await state.clear()

    await message.answer(
        "Вещь сохранена. Вернуться в меню или добавить ещё?",
        reply_markup=main_menu(),
    )


@router.message(ItemAddStates.waiting_for_item_photo)
async def prompt_photo_format(message: Message) -> None:
    await message.answer("Пришлите фото (JPG/PNG) с вещью. Размер до 10 МБ.")


