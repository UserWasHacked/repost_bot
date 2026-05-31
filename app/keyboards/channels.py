from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from app.models.channel import TelegramChannel


def channels_list_keyboard(channels: list[TelegramChannel]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for ch in channels:
        title = ch.title[:30] + "..." if len(ch.title) > 30 else ch.title
        status = "✅" if ch.is_active else "❌"
        builder.button(
            text=f"{status} {title}",
            callback_data=f"channel:view:{ch.id}",
        )
    builder.button(text="➕ Добавить канал", callback_data="channel:add")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def channel_settings_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать пост", callback_data=f"post:create:{channel_id}")
    builder.button(text="⏰ Расписание", callback_data=f"schedule:view:{channel_id}")
    builder.button(text="📋 Очередь", callback_data=f"queue:view:{channel_id}")
    builder.button(text="🤖 Настройки ИИ", callback_data=f"channel:ai:{channel_id}")
    builder.button(text="🔄 Активность", callback_data=f"channel:toggle:{channel_id}")
    builder.button(text="🗑 Удалить канал", callback_data=f"channel:delete:{channel_id}")
    builder.button(text="◀️ Назад к списку", callback_data="menu:channels")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def confirm_delete_channel_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Да, удалить", callback_data=f"channel:delete_confirm:{channel_id}")
    builder.button(text="❌ Отмена", callback_data=f"channel:view:{channel_id}")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()
