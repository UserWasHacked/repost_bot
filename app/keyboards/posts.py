from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

from app.models.post import Post


def post_actions_keyboard(post_id: int, channel_id: int, status: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if status in ("draft", "queued"):
        builder.button(text="📤 Опубликовать сейчас", callback_data=f"post:publish:{post_id}")
        builder.button(text="⏳ Отложить", callback_data=f"post:schedule:{post_id}")
        builder.button(text="📝 Редактировать", callback_data=f"post:edit:{post_id}")

    if status in ("draft", "scheduled", "queued"):
        builder.button(text="👁 Предпросмотр", callback_data=f"post:preview:{post_id}")

    builder.button(text="🗑 Удалить", callback_data=f"post:delete:{post_id}")
    builder.button(text="◀️ Назад", callback_data=f"channel:view:{channel_id}")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def queue_keyboard(posts: list[Post], channel_id: int, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    for post in posts:
        preview = (post.text or "[без текста]")[:40] + "..." if post.text else "[медиа]"
        status_emoji = {
            "draft": "📝",
            "scheduled": "⏳",
            "queued": "📋",
            "published": "✅",
            "failed": "❌",
        }.get(post.status.value if hasattr(post.status, 'value') else post.status, "📝")
        builder.button(
            text=f"{status_emoji} {preview}",
            callback_data=f"post:view:{post.id}",
        )

    if len(posts) > 0:
        nav_row = []
        if page > 0:
            nav_row.append({"text": "⬅️", "callback_data": f"queue:page:{channel_id}:{page - 1}"})
        nav_row.append({"text": "➕ Новый пост", "callback_data": f"post:create:{channel_id}"})
        if len(posts) == 10:
            nav_row.append({"text": "➡️", "callback_data": f"queue:page:{channel_id}:{page + 1}"})
        for btn in nav_row:
            builder.button(text=btn["text"], callback_data=btn["callback_data"])
    else:
        builder.button(text="➕ Создать первый пост", callback_data=f"post:create:{channel_id}")

    builder.button(text="◀️ Назад к каналу", callback_data=f"channel:view:{channel_id}")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()


def publish_now_or_schedule_keyboard(post_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📤 Сейчас", callback_data=f"post:publish:{post_id}")
    builder.button(text="⏳ Отложить", callback_data=f"post:schedule:{post_id}")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(2, 1)
    return builder.as_markup()


def post_creation_keyboard(channel_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✍️ Написать текст", callback_data=f"post:write_text:{channel_id}")
    builder.button(text="🖼 Добавить изображение", callback_data=f"post:add_image:{channel_id}")
    builder.button(text="🤖 Сгенерировать ИИ", callback_data=f"post:ai:{channel_id}")
    builder.button(text="◀️ Отмена", callback_data=f"channel:view:{channel_id}")
    builder.button(text="◀️ На главную", callback_data="menu:main")
    builder.adjust(1)
    return builder.as_markup()
