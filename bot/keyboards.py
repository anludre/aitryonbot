from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Примерить одежду"), KeyboardButton(text="Мои вещи")],
            [KeyboardButton(text="Мои образы"), KeyboardButton(text="Гид по фото")],
            [KeyboardButton(text="Тарифы"), KeyboardButton(text="Поддержка")],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие",
    )


def items_empty_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="+ Добавить вещь", callback_data="items:add")],
        ]
    )


def items_list_keyboard(items: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    """
    Build inline keyboard for items list.
    items: list of (item_id, title)
    """
    rows: list[list[InlineKeyboardButton]] = []
    for item_id, title in items[:5]:
        rows.append([InlineKeyboardButton(text=title, callback_data=f"items:choose:{item_id}")])
    rows.append([InlineKeyboardButton(text="+ Добавить вещь", callback_data="items:add")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="В меню", callback_data="nav:menu")]]
    )


