from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.schedule import (
    schedule_list_keyboard,
    schedule_actions_keyboard,
)
from app.utils.helpers import AI_TOPICS_RU
from app.keyboards.channels import channel_settings_keyboard
from app.database.repository import BaseRepository
from app.models.schedule import Schedule
from app.services.scheduler import SchedulerService
from app.utils.logger import get_logger
from app.utils.validators import validate_interval, validate_time, validate_positive_int

router = Router()
logger = get_logger(__name__)


class ScheduleState(StatesGroup):
    waiting_for_type = State()
    waiting_for_interval = State()
    waiting_for_time = State()
    waiting_for_day = State()
    waiting_for_ai_topic = State()
    waiting_for_length = State()
    waiting_for_emotionality = State()
    waiting_for_paragraphs = State()


@router.callback_query(F.data.startswith("schedule:view:"))
async def view_schedules(callback: CallbackQuery, user, db_session):
    channel_id = int(callback.data.split(":")[2])
    repo = BaseRepository(Schedule, db_session)
    schedules = await repo.list(channel_id=channel_id)

    text = f"⏰ <b>Расписания канала</b>\n\n"
    if not schedules:
        text += "Расписаний пока нет. Создайте новое расписание."

    await callback.message.edit_text(
        text, reply_markup=schedule_list_keyboard(schedules, channel_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("schedule:add:"))
async def add_schedule_start(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split(":")[2])
    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(
        "⏰ <b>Создание расписания</b>\n\n"
        "Выберите тип расписания:\n\n"
        "1 — Интервал (каждые N часов)\n"
        "2 — Конкретное время ежедневно\n"
        "3 — Конкретное время еженедельно\n\n"
        "Отправьте номер (1, 2 или 3):"
    )
    await state.set_state(ScheduleState.waiting_for_type)
    await callback.answer()


@router.message(ScheduleState.waiting_for_type)
async def schedule_type_received(message: Message, state: FSMContext):
    choice = message.text.strip()

    if choice == "1":
        await message.answer("Введите интервал в часах (например: 4, 0.5 для 30 минут):")
        await state.set_state(ScheduleState.waiting_for_interval)
    elif choice == "2":
        await message.answer("Введите время в формате ЧЧ:ММ (например: 09:00):")
        await state.set_state(ScheduleState.waiting_for_time)
    elif choice == "3":
        await message.answer("Введите время в формате ЧЧ:ММ (например: 09:00):")
        await state.update_data(schedule_type="weekly")
        await state.set_state(ScheduleState.waiting_for_time)
    else:
        await message.answer("❌ Отправьте 1, 2 или 3.")


@router.message(ScheduleState.waiting_for_interval)
async def schedule_interval_received(message: Message, state: FSMContext):
    interval = validate_interval(message.text.strip())
    if interval is None:
        await message.answer("❌ Неверный интервал. Введите число от 0.1 до 720.")
        return

    await state.update_data(
        interval_hours=interval,
        name=f"Каждые {interval}ч",
    )
    await message.answer(
        "Выберите темы для ИИ-генерации (можно несколько через запятую, например: 1,3,8):\n\n"
        "1 — ☀️ Доброе утро\n"
        "2 — 🌙 Спокойной ночи\n"
        "3 — 🤗 Поддержка\n"
        "4 — 🙏 Благодарность\n"
        "5 — 💭 Мысли о человеке\n"
        "6 — 🫧 Жизненные размышления\n"
        "7 — 🤝 Доверие\n"
        "8 — 💗 Привязанность\n"
        "9 — 📸 Воспоминания\n"
        "10 — 💬 Ценность общения\n\n"
        "Или отправьте «нет» — будут публиковаться посты из очереди без ИИ."
    )
    await state.set_state(ScheduleState.waiting_for_ai_topic)


@router.message(ScheduleState.waiting_for_time)
async def schedule_time_received(message: Message, user, db_session, state: FSMContext):
    time_str = validate_time(message.text.strip())
    if time_str is None:
        await message.answer("❌ Неверное время. Используйте формат ЧЧ:ММ.")
        return

    data = await state.get_data()
    channel_id = data["channel_id"]
    schedule_type = data.get("schedule_type", "daily")

    if schedule_type == "weekly":
        await state.update_data(time_str=time_str)
        await message.answer(
            "Введите день недели (0-6, где 0=Пн, 1=Вт, ..., 6=Вс):"
        )
        await state.set_state(ScheduleState.waiting_for_day)
    else:
        await state.update_data(
            time_str=time_str,
            name=f"Ежедневно в {time_str}",
            daily=True,
        )
        await message.answer(
            "Выберите темы для ИИ-генерации (можно несколько через запятую, например: 1,3,8):\n\n"
            "1 — ☀️ Доброе утро\n"
            "2 — 🌙 Спокойной ночи\n"
            "3 — 🤗 Поддержка\n"
            "4 — 🙏 Благодарность\n"
            "5 — 💭 Мысли о человеке\n"
            "6 — 🫧 Жизненные размышления\n"
            "7 — 🤝 Доверие\n"
            "8 — 💗 Привязанность\n"
            "9 — 📸 Воспоминания\n"
            "10 — 💬 Ценность общения\n\n"
            "Или отправьте «нет» — будут публиковаться посты из очереди без ИИ."
        )
        await state.set_state(ScheduleState.waiting_for_ai_topic)


@router.message(ScheduleState.waiting_for_time)
async def schedule_time_received(message: Message, user, db_session, state: FSMContext):
    time_str = validate_time(message.text.strip())
    if time_str is None:
        await message.answer("❌ Неверное время. Используйте формат ЧЧ:ММ.")
        return

    data = await state.get_data()
    channel_id = data["channel_id"]
    schedule_type = data.get("schedule_type", "daily")

    if schedule_type == "weekly":
        await state.update_data(time_str=time_str)
        await message.answer(
            "Введите день недели (0-6, где 0=Пн, 1=Вт, ..., 6=Вс):"
        )
        await state.set_state(ScheduleState.waiting_for_day)
    else:
        await state.update_data(
            time_str=time_str,
            name=f"Ежедневно в {time_str}",
            daily=True,
        )
    await message.answer(
        "Выберите темы для ИИ-генерации (можно несколько через запятую, например: 1,3,8):\n\n"
        "1 — ☀️ Доброе утро\n"
        "2 — 🌙 Спокойной ночи\n"
        "3 — 🤗 Поддержка\n"
        "4 — 🙏 Благодарность\n"
        "5 — 💭 Мысли о человеке\n"
        "6 — 🫧 Жизненные размышления\n"
        "7 — 🤝 Доверие\n"
        "8 — 💗 Привязанность\n"
        "9 — 📸 Воспоминания\n"
        "10 — 💬 Ценность общения\n\n"
        "Или отправьте «нет» — будут публиковаться посты из очереди без ИИ."
    )
    await state.set_state(ScheduleState.waiting_for_ai_topic)


AI_TOPICS_MAP = {
    "1": "morning_greeting",
    "2": "night_greeting",
    "3": "support",
    "4": "gratitude",
    "5": "thinking_of_you",
    "6": "life_reflection",
    "7": "trust",
    "8": "affection",
    "9": "memories",
    "10": "communication_value",
}


@router.message(ScheduleState.waiting_for_ai_topic)
async def schedule_ai_topic_received(message: Message, user, db_session, state: FSMContext):
    data = await state.get_data()
    choice = message.text.strip().lower()
    channel_id = data["channel_id"]

    ai_topics = []
    if choice != "нет":
        parts = [p.strip() for p in choice.split(",")]
        for part in parts:
            topic_key = AI_TOPICS_MAP.get(part)
            if topic_key is None:
                await message.answer(f"❌ Неверный номер: {part}. Отправьте номера от 1 до 10 через запятую или «нет».")
                return
            ai_topics.append(topic_key)

    ai_topic_str = ",".join(ai_topics) if ai_topics else None

    specific_time = None
    if "time_str" in data:
        hours, minutes = map(int, data["time_str"].split(":"))
        from datetime import time
        specific_time = time(hours, minutes)

    repo = BaseRepository(Schedule, db_session)
    schedule = await repo.create(
        channel_id=channel_id,
        name=data.get("name", "Расписание"),
        interval_hours=data.get("interval_hours"),
        specific_time=specific_time,
        daily=data.get("daily", False),
        weekly=data.get("weekly", False),
        weekly_day=data.get("weekly_day"),
        is_enabled=True,
        ai_generated=ai_topic_str is not None,
        ai_topic=ai_topic_str,
        ai_tone="warm",
    )

    scheduler_service = SchedulerService()
    await scheduler_service.add_schedule_job(schedule)

    topic_labels = [AI_TOPICS_RU.get(t, t) for t in ai_topics] if ai_topics else ["без ИИ"]
    await message.answer(
        f"✅ Расписание «{schedule.name}» создано!\nТемы: {', '.join(topic_labels)}",
        reply_markup=channel_settings_keyboard(channel_id),
    )
    await state.clear()


@router.callback_query(F.data.startswith("schedule:edit:"))
async def edit_schedule(callback: CallbackQuery, user, db_session):
    schedule_id = int(callback.data.split(":")[2])
    repo = BaseRepository(Schedule, db_session)
    schedule = await repo.get(schedule_id)

    if schedule is None:
        await callback.message.edit_text("❌ Расписание не найдено.")
        await callback.answer()
        return

    type_text = []
    if schedule.interval_hours:
        type_text.append(f"🔄 Каждые {schedule.interval_hours}ч")
    if schedule.daily and schedule.specific_time:
        type_text.append(f"📅 Ежедневно в {schedule.specific_time.strftime('%H:%M')}")
    if schedule.weekly and schedule.specific_time:
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = days[schedule.weekly_day] if schedule.weekly_day is not None else "?"
        type_text.append(f"📅 Еженедельно {day_name} в {schedule.specific_time.strftime('%H:%M')}")

    status = "✅ Активно" if schedule.is_enabled else "❌ Остановлено"

    text = (
        f"⏰ <b>Расписание: {schedule.name}</b>\n\n"
        f"Тип: {', '.join(type_text)}\n"
        f"Статус: {status}\n"
    )
    if schedule.ai_generated:
        text += (
            f"\n🤖 ИИ-генерация: Включена\n"
            f"Тема: {schedule.ai_topic or 'Не задана'}\n"
            f"Длина текста: {schedule.text_length or 200} символов\n"
        )

    await callback.message.edit_text(
        text, reply_markup=schedule_actions_keyboard(schedule_id, schedule.channel_id, schedule.is_enabled)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("schedule:toggle:"))
async def toggle_schedule(callback: CallbackQuery, user, db_session):
    schedule_id = int(callback.data.split(":")[2])
    repo = BaseRepository(Schedule, db_session)
    schedule = await repo.get(schedule_id)

    if schedule is None:
        await callback.message.edit_text("❌ Расписание не найдено.")
        await callback.answer()
        return

    await repo.update(schedule_id, is_enabled=not schedule.is_enabled)
    scheduler_service = SchedulerService()

    if not schedule.is_enabled:
        await scheduler_service.remove_schedule_job(schedule_id)
    else:
        schedule = await repo.get(schedule_id)
        await scheduler_service.add_schedule_job(schedule)

    await edit_schedule(callback, user, db_session)


@router.callback_query(F.data.startswith("schedule:delete:"))
async def delete_schedule(callback: CallbackQuery, user, db_session):
    schedule_id = int(callback.data.split(":")[2])
    repo = BaseRepository(Schedule, db_session)
    schedule = await repo.get(schedule_id)
    channel_id = schedule.channel_id if schedule else None

    scheduler_service = SchedulerService()
    await scheduler_service.remove_schedule_job(schedule_id)
    await repo.delete(schedule_id)

    if channel_id:
        await callback.message.edit_text(
            "✅ Расписание удалено.",
            reply_markup=channel_settings_keyboard(channel_id),
        )
    else:
        await callback.message.edit_text("✅ Расписание удалено.")
    await callback.answer()
