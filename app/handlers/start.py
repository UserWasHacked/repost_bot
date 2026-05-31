from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart

from app.keyboards.main import main_menu_keyboard
from app.utils.logger import get_logger
from app.services.statistics import StatisticsService
from app.keyboards.main import back_to_main_button

router = Router()
logger = get_logger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message, user, db_session):
    text = (
        f"👋 Привет, {user.first_name or 'пользователь'}!\n\n"
        "Я — бот для автоматического ведения Telegram-каналов.\n\n"
        "Я умею:\n"
        "📢 Управлять несколькими каналами\n"
        "📝 Создавать и публиковать посты\n"
        "⏰ Работать по расписанию\n"
        "🤖 Генерировать тексты через ИИ\n\n"
        "Выбери действие в меню ниже:"
    )
    await message.answer(text, reply_markup=main_menu_keyboard())


@router.callback_query(F.data == "menu:main")
async def main_menu_callback(callback: CallbackQuery, user):
    await callback.message.edit_text(
        f"👋 Главное меню, {user.first_name or 'пользователь'}!\n\n"
        "Выбери действие:",
        reply_markup=main_menu_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:statistics")
async def statistics_callback(callback: CallbackQuery, user, db_session):
    stats_service = StatisticsService(db_session)
    stats = await stats_service.get_user_stats(user.id)

    text = (
        "📊 <b>Общая статистика</b>\n\n"
        f"📢 Подключено каналов: <b>{stats['channel_count']}</b>\n"
        f"📝 Всего постов: <b>{stats['total_posts']}</b>\n"
        f"✅ Опубликовано: <b>{stats['total_published']}</b>\n"
    )
    await callback.message.edit_text(text, reply_markup=back_to_main_button())
    await callback.answer()
