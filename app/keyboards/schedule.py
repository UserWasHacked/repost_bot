from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from app.models.schedule import Schedule


def schedule_list_keyboard(schedules: list[Schedule], channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for s in schedules:
        status = "✅" if s.is_enabled else "❌"
        name = s.name[:25] + "..." if len(s.name) > 25 else s.name
        builder.button(
            text=f"{status} {name}",
            callback_data=f"schedule:edit:{s.id}",
        )
    builder.button(text="➕ Добавить расписание", callback_data=f"schedule:add:{channel_id}")
    builder.button(text="◀️ Назад к каналу", callback_data=f"channel:view:{channel_id}")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def schedule_actions_keyboard(schedule_id: int, channel_id: int, is_enabled: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    toggle_text = "⏸ Остановить" if is_enabled else "▶️ Запустить"
    builder.button(text=toggle_text, callback_data=f"schedule:toggle:{schedule_id}")
    builder.button(text="✏️ Редактировать", callback_data=f"schedule:edit:{schedule_id}")
    builder.button(text="🗑 Удалить", callback_data=f"schedule:delete:{schedule_id}")
    builder.button(text="◀️ Назад", callback_data=f"schedule:view:{channel_id}")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def ai_topic_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    topics = [
        ("morning_greeting", "☀️ Доброе утро"),
        ("night_greeting", "🌙 Спокойной ночи"),
        ("support", "🤗 Поддержка"),
        ("gratitude", "🙏 Благодарность"),
        ("thinking_of_you", "💭 Мысли о человеке"),
        ("life_reflection", "🫧 Жизненные размышления"),
        ("trust", "🤝 Доверие"),
        ("affection", "💗 Привязанность"),
        ("memories", "📸 Воспоминания"),
        ("communication_value", "💬 Ценность общения"),
    ]
    for value, label in topics:
        builder.button(text=label, callback_data=f"ai:topic:{channel_id}:{value}")
    builder.button(text="◀️ Назад", callback_data=f"post:create:{channel_id}")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(2, 1)
    return builder.as_markup()
