from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.channels import (
    channels_list_keyboard,
    channel_settings_keyboard,
    confirm_delete_channel_keyboard,
)
from app.keyboards.main import back_to_main_button
from app.services.channel import ChannelService
from app.utils.logger import get_logger
from app.utils.validators import validate_channel_link, validate_channel_id

router = Router()
logger = get_logger(__name__)


class AddChannelState(StatesGroup):
    waiting_for_id = State()


@router.callback_query(F.data == "menu:channels")
async def list_channels_callback(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    service = ChannelService(db_session, bot)
    channels = await service.list_user_channels(user.id)

    if not channels:
        text = "📢 У вас нет подключенных каналов.\n\nНажми «➕ Добавить канал», чтобы подключить первый канал."
        builder = channels_list_keyboard([])
        await callback.message.edit_text(text, reply_markup=builder)
    else:
        text = "📢 <b>Мои каналы</b>\n\nВыберите канал для управления:"
        await callback.message.edit_text(text, reply_markup=channels_list_keyboard(channels))

    await callback.answer()


@router.callback_query(F.data.startswith("channel:add"))
async def add_channel_start(callback: CallbackQuery, state: FSMContext):
    text = (
        "➕ <b>Добавление канала</b>\n\n"
        "Отправьте мне ID канала или ссылку на канал.\n\n"
        "ID канала выглядит как <code>-1001234567890</code>\n"
        "Ссылка выглядит как <code>https://t.me/channel_name</code>\n\n"
        "⚠️ Бот должен быть администратором канала!"
    )
    await callback.message.edit_text(text)
    await state.set_state(AddChannelState.waiting_for_id)
    await callback.answer()


@router.message(AddChannelState.waiting_for_id)
async def add_channel_process(message: Message, user, db_session, state: FSMContext):
    bot = message.bot
    text = message.text.strip() if message.text else ""

    channel_id = None
    username = validate_channel_link(text)
    if username:
        try:
            chat = await bot.get_chat(f"@{username}")
            channel_id = chat.id
        except Exception:
            await message.answer("❌ Не удалось найти канал по этой ссылке. Проверьте ссылку и попробуйте снова.")
            return
    elif text.lstrip("-").isdigit():
        channel_id = int(text)
    else:
        await message.answer("❌ Неверный формат. Отправьте ID канала или ссылку вида https://t.me/...")
        return

    service = ChannelService(db_session, bot)
    result = await service.add_channel(channel_id, user)

    if result:
        await message.answer(
            f"✅ Канал <b>{result.title}</b> успешно подключен!",
            reply_markup=channel_settings_keyboard(result.id),
        )
    else:
        await message.answer(
            "❌ Не удалось добавить канал.\n\n"
            "Проверьте:\n"
            "1. Бот является администратором канала\n"
            "2. ID канала указан верно\n"
            "3. У бота есть права на отправку сообщений"
        )

    await state.clear()


@router.callback_query(F.data.startswith("channel:view:"))
async def channel_view_callback(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    channel_id = int(callback.data.split(":")[2])
    service = ChannelService(db_session, bot)
    channel = await service.get_channel(channel_id)

    if channel is None:
        await callback.message.edit_text("❌ Канал не найден.")
        await callback.answer()
        return

    status_text = "✅ Активен" if channel.is_active else "❌ Неактивен"
    schedule_text = []
    if channel.schedule_interval_hours:
        schedule_text.append(f"🔄 Каждые {channel.schedule_interval_hours}ч")
    if channel.schedule_time:
        schedule_text.append(f"⏰ В {channel.schedule_time.strftime('%H:%M')}")
    if channel.schedule_daily:
        schedule_text.append("📅 Ежедневно")
    schedule_str = ", ".join(schedule_text) if schedule_text else "Не настроено"

    text = (
        f"📢 <b>{channel.title}</b>\n\n"
        f"🆔 ID: <code>{channel.id}</code>\n"
        f"📊 Статус: {status_text}\n"
        f"⏰ Расписание: {schedule_str}\n"
    )

    await callback.message.edit_text(text, reply_markup=channel_settings_keyboard(channel_id))
    await callback.answer()


@router.callback_query(F.data.startswith("channel:toggle:"))
async def channel_toggle_callback(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    channel_id = int(callback.data.split(":")[2])
    service = ChannelService(db_session, bot)
    await service.toggle_active(channel_id)

    channel = await service.get_channel(channel_id)
    status = "активирован" if channel.is_active else "деактивирован"
    await callback.message.edit_text(
        f"✅ Канал <b>{channel.title}</b> {status}.",
        reply_markup=channel_settings_keyboard(channel_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("channel:delete:"))
async def channel_delete_start(callback: CallbackQuery):
    channel_id = int(callback.data.split(":")[2])
    await callback.message.edit_text(
        "⚠️ <b>Вы уверены, что хотите удалить канал?</b>\n\n"
        "Все посты и расписания этого канала будут удалены.",
        reply_markup=confirm_delete_channel_keyboard(channel_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("channel:delete_confirm:"))
async def channel_delete_confirm(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    channel_id = int(callback.data.split(":")[2])
    service = ChannelService(db_session, bot)
    channel = await service.get_channel(channel_id)
    title = channel.title if channel else "канал"
    await service.remove_channel(channel_id)

    await callback.message.edit_text(
        f"✅ Канал <b>{title}</b> удален.",
        reply_markup=back_to_main_button(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("channel:ai:"))
async def channel_ai_settings(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    channel_id = int(callback.data.split(":")[2])
    service = ChannelService(db_session, bot)
    channel = await service.get_channel(channel_id)

    if channel is None:
        await callback.message.edit_text("❌ Канал не найден.")
        await callback.answer()
        return

    ai_status = "✅ Включена" if channel.allow_ai_generation else "❌ Выключена"
    text = (
        f"🤖 <b>Настройки ИИ для канала {channel.title}</b>\n\n"
        f"Генерация: {ai_status}\n"
        f"Тональность: {channel.ai_tone}\n\n"
        "Настройки генерации можно изменить в главном меню."
    )
    await callback.message.edit_text(text, reply_markup=channel_settings_keyboard(channel_id))
    await callback.answer()
