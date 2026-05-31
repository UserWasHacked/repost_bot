from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from app.config import settings
from app.database.session import async_session_factory
from app.database.repository import BaseRepository
from app.models.user import User
from app.keyboards.main import back_to_main_button
from app.utils.logger import get_logger

router = Router()
logger = get_logger(__name__)


async def is_admin(user) -> bool:
    return user.is_admin or user.id in settings.admin_ids


@router.message(Command("admin"))
async def admin_panel(message: Message, user):
    if not await is_admin(user):
        await message.answer("❌ У вас нет доступа к панели администратора.")
        return

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Пользователи", callback_data="admin:users")
    builder.button(text="📊 Системная статистика", callback_data="admin:stats")
    builder.button(text="🔄 Перезагрузить расписания", callback_data="admin:reload_schedules")
    builder.adjust(1)

    await message.answer(
        "🔐 <b>Панель администратора</b>\n\n"
        "Управление ботом и пользователями.",
        reply_markup=builder.as_markup(),
    )


@router.callback_query(F.data.startswith("admin:"))
async def admin_callbacks(callback: CallbackQuery, user):
    if not await is_admin(user):
        await callback.answer("❌ Нет доступа", show_alert=True)
        return

    action = callback.data.split(":")[1]

    if action == "users":
        async with async_session_factory() as session:
            repo = BaseRepository(User, session)
            users = await repo.list()
            text = "👥 <b>Пользователи</b>\n\n"
            for u in users:
                name = u.first_name or u.username or str(u.id)
                text += f"• {name} ({u.id}) {'⭐ Админ' if u.is_admin else ''}\n"
            await callback.message.edit_text(text, reply_markup=back_to_main_button())

    elif action == "stats":
        async with async_session_factory() as session:
            from app.models.channel import TelegramChannel
            from app.models.post import Post

            user_repo = BaseRepository(User, session)
            channel_repo = BaseRepository(TelegramChannel, session)
            post_repo = BaseRepository(Post, session)

            users = await user_repo.list()
            channels = await channel_repo.list()
            posts = await post_repo.list()

            text = (
                "📊 <b>Системная статистика</b>\n\n"
                f"👥 Пользователей: <b>{len(users)}</b>\n"
                f"📢 Каналов: <b>{len(channels)}</b>\n"
                f"📝 Всего постов: <b>{len(posts)}</b>\n"
            )
            await callback.message.edit_text(text, reply_markup=back_to_main_button())

    elif action == "reload_schedules":
        from app.services.scheduler import SchedulerService

        scheduler_service = SchedulerService()
        await scheduler_service.load_all_schedules()
        await callback.message.edit_text(
            "✅ Расписания перезагружены.",
            reply_markup=back_to_main_button(),
        )

    await callback.answer()


@router.message(Command("broadcast"))
async def broadcast(message: Message, user):
    if not await is_admin(user):
        await message.answer("❌ Нет доступа")
        return

    text = message.text.removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Использование: /broadcast <текст>")
        return

    async with async_session_factory() as session:
        repo = BaseRepository(User, session)
        users = await repo.list()
        sent = 0
        for u in users:
            try:
                await message.bot.send_message(chat_id=u.id, text=text)
                sent += 1
            except Exception:
                pass

    await message.answer(f"✅ Рассылка отправлена {sent} пользователям.")
