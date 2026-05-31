from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📢 Мои каналы", callback_data="menu:channels")
    builder.button(text="📝 Очередь публикаций", callback_data="menu:queue")
    builder.button(text="📊 Статистика", callback_data="menu:statistics")
    builder.button(text="⚙️ Настройки генерации", callback_data="menu:ai_settings")
    builder.adjust(1)
    return builder.as_markup()


def back_to_main_button() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ На главную", callback_data="menu:main")
    return builder.as_markup()
