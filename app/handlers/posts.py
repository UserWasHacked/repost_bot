from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime

from app.keyboards.posts import (
    post_actions_keyboard,
    queue_keyboard,
    post_creation_keyboard,
    publish_now_or_schedule_keyboard,
)
from app.keyboards.channels import channel_settings_keyboard
from app.services.post import PostService
from app.models.post import PostStatus, PostType
from app.services.publisher import PublisherService

from app.utils.logger import get_logger
from app.utils.helpers import format_datetime

router = Router()
logger = get_logger(__name__)


class CreatePostState(StatesGroup):
    waiting_for_text = State()
    waiting_for_image = State()
    waiting_for_schedule_time = State()
    waiting_for_edit_text = State()


@router.callback_query(F.data.startswith("post:create:"))
async def create_post_start(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split(":")[2])
    await state.update_data(channel_id=channel_id, media_file_ids=None, post_type=PostType.text)

    await callback.message.edit_text(
        "📝 <b>Создание поста</b>\n\n"
        "Выберите, что хотите добавить:",
        reply_markup=post_creation_keyboard(channel_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("post:write_text:"))
async def post_write_text_start(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split(":")[2])
    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(
        "✍️ Отправьте текст поста:"
    )
    await state.set_state(CreatePostState.waiting_for_text)
    await callback.answer()


@router.message(CreatePostState.waiting_for_text)
async def post_text_received(message: Message, user, db_session, state: FSMContext):
    data = await state.get_data()
    channel_id = data["channel_id"]
    text = message.text or message.caption or ""
    media_ids = data.get("media_file_ids")
    post_type = data.get("post_type", PostType.text)

    if message.photo:
        if post_type == PostType.text:
            post_type = PostType.image
            media_ids = message.photo[-1].file_id
        elif media_ids:
            media_ids = media_ids + "|" + message.photo[-1].file_id
            post_type = PostType.multi_image
        else:
            media_ids = message.photo[-1].file_id
            post_type = PostType.image

    bot = message.bot
    service = PostService(db_session, bot)
    post = await service.create_post(
        channel_id=channel_id,
        author=user,
        text=text,
        post_type=post_type,
        media_file_ids=media_ids,
    )

    prefix = "✅ Пост создан!\n\n"
    body = text if len(text) + len(prefix) <= 4096 else text[: 4096 - len(prefix) - 3] + "..."
    await message.answer(
        f"{prefix}{body}",
        reply_markup=publish_now_or_schedule_keyboard(post.id),
    )
    await state.clear()


@router.callback_query(F.data.startswith("post:add_image:"))
async def post_add_image(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split(":")[2])
    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(
        "🖼 Отправьте изображение (можно несколько одним сообщением):"
    )
    await state.set_state(CreatePostState.waiting_for_image)
    await callback.answer()


@router.message(CreatePostState.waiting_for_image)
async def post_image_received(message: Message, user, db_session, state: FSMContext):
    data = await state.get_data()
    channel_id = data["channel_id"]
    text = message.caption or ""

    if not message.photo:
        await message.answer("❌ Пожалуйста, отправьте изображение.")
        return

    media_ids = message.photo[-1].file_id
    post_type = PostType.image

    if message.media_group_id:
        post_type = PostType.multi_image

    bot = message.bot
    service = PostService(db_session, bot)
    post = await service.create_post(
        channel_id=channel_id,
        author=user,
        text=text,
        post_type=post_type,
        media_file_ids=media_ids,
    )

    await message.answer(
        f"✅ Пост с изображением создан!",
        reply_markup=publish_now_or_schedule_keyboard(post.id),
    )
    await state.clear()


@router.callback_query(F.data.startswith("post:publish:"))
async def publish_post_now(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    post_id = int(callback.data.split(":")[2])
    publisher = PublisherService(db_session, bot)
    success = await publisher.publish_post(post_id)

    if success:
        await callback.message.edit_text("✅ Пост опубликован!")
    else:
        await callback.message.edit_text("❌ Ошибка публикации. Проверьте права бота.")

    await callback.answer()


@router.callback_query(F.data.startswith("post:schedule:"))
async def schedule_post_start(callback: CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split(":")[2])
    await state.update_data(post_id=post_id)

    await callback.message.edit_text(
        "⏳ Введите дату и время публикации в формате:\n\n"
        "<code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n\n"
        "Например: <code>25.12.2025 15:30</code>"
    )
    await state.set_state(CreatePostState.waiting_for_schedule_time)
    await callback.answer()


@router.message(CreatePostState.waiting_for_schedule_time)
async def schedule_time_received(message: Message, user, db_session, state: FSMContext):
    data = await state.get_data()
    post_id = data["post_id"]

    try:
        scheduled_at = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
    except ValueError:
        await message.answer(
            "❌ Неверный формат. Используйте <code>ДД.ММ.ГГГГ ЧЧ:ММ</code>\n"
            "Например: <code>25.12.2025 15:30</code>"
        )
        return

    bot = message.bot
    service = PostService(db_session, bot)
    await service.update_post(post_id, scheduled_at=scheduled_at)

    from app.services.scheduler import SchedulerService

    scheduler_service = SchedulerService()
    await scheduler_service.schedule_post(post_id, scheduled_at)

    await message.answer(
        f"✅ Пост запланирован на {scheduled_at.strftime('%d.%m.%Y %H:%M')}",
    )
    await state.clear()


@router.callback_query(F.data.startswith("post:view:"))
async def view_post(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    post_id = int(callback.data.split(":")[2])
    service = PostService(db_session, bot)
    post = await service.get_post(post_id)

    if post is None:
        await callback.message.edit_text("❌ Пост не найден.")
        await callback.answer()
        return

    status_labels = {
        PostStatus.draft: "📝 Черновик",
        PostStatus.scheduled: "⏳ Запланирован",
        PostStatus.queued: "📋 В очереди",
        PostStatus.published: "✅ Опубликован",
        PostStatus.failed: "❌ Ошибка",
    }
    status_text = status_labels.get(post.status, str(post.status))

    header = (
        f"📝 <b>Пост #{post.id}</b>\n\n"
        f"Статус: {status_text}\n"
        f"Тип: {post.post_type.value}\n"
        f"Создан: {format_datetime(post.created_at)}\n"
    )
    if post.scheduled_at:
        header += f"Запланирован: {format_datetime(post.scheduled_at)}\n"
    if post.published_at:
        header += f"Опубликован: {format_datetime(post.published_at)}\n"
    if post.is_ai_generated:
        header += "🤖 Сгенерировано ИИ\n"

    body = post.text or "[без текста]"
    full = f"{header}\n{body}"
    if len(full) > 4096:
        cutoff = 4096 - len(header) - 4
        full = f"{header}\n{body[:cutoff]}..."

    await callback.message.edit_text(
        full,
        reply_markup=post_actions_keyboard(post_id, post.channel_id, post.status.value)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("post:preview:"))
async def preview_post(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    post_id = int(callback.data.split(":")[2])
    publisher = PublisherService(db_session, bot)
    success = await publisher.send_preview(post_id, callback.from_user.id)

    if success:
        await callback.answer("✅ Предпросмотр отправлен в личные сообщения")
    else:
        await callback.answer("❌ Не удалось показать предпросмотр")


@router.callback_query(F.data.startswith("post:edit:"))
async def edit_post_start(callback: CallbackQuery, state: FSMContext):
    post_id = int(callback.data.split(":")[2])
    await state.update_data(post_id=post_id)

    await callback.message.edit_text(
        "✍️ Отправьте новый текст для этого поста:"
    )
    await state.set_state(CreatePostState.waiting_for_edit_text)
    await callback.answer()


@router.message(CreatePostState.waiting_for_edit_text)
async def edit_post_text_received(message: Message, user, db_session, state: FSMContext):
    data = await state.get_data()
    post_id = data["post_id"]
    new_text = message.text or ""

    bot = message.bot
    service = PostService(db_session, bot)
    await service.update_post(post_id, text=new_text)

    post = await service.get_post(post_id)
    await message.answer(
        "✅ Текст поста обновлен!",
        reply_markup=post_actions_keyboard(post_id, post.channel_id, post.status.value) if post else None,
    )
    await state.clear()


@router.callback_query(F.data.startswith("post:delete:"))
async def delete_post(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    post_id = int(callback.data.split(":")[2])
    service = PostService(db_session, bot)
    post = await service.get_post(post_id)
    channel_id = post.channel_id if post else None

    await service.delete_post(post_id)

    if channel_id:
        await callback.message.edit_text(
            "✅ Пост удален.",
            reply_markup=channel_settings_keyboard(channel_id),
        )
    else:
        await callback.message.edit_text("✅ Пост удален.")

    await callback.answer()


@router.callback_query(F.data.startswith("queue:view:"))
async def view_queue(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    channel_id = int(callback.data.split(":")[2])
    service = PostService(db_session, bot)
    posts = await service.list_queue(channel_id)

    text = f"📋 <b>Очередь публикаций</b>\n\n"
    if not posts:
        text += "Очередь пуста."
    else:
        text += f"В очереди: <b>{len(posts)}</b> постов\n"

    await callback.message.edit_text(
        text, reply_markup=queue_keyboard(posts, channel_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("queue:page:"))
async def queue_page(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    parts = callback.data.split(":")
    channel_id = int(parts[2])
    page = int(parts[3])

    service = PostService(db_session, bot)
    posts = await service.list_queue(channel_id)

    start = page * 10
    page_posts = posts[start: start + 10]

    await callback.message.edit_text(
        f"📋 <b>Очередь публикаций</b> (стр. {page + 1})",
        reply_markup=queue_keyboard(page_posts, channel_id, page),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:queue")
async def all_channels_queue(callback: CallbackQuery, user, db_session):
    bot = callback.bot
    from app.services.channel import ChannelService

    channel_service = ChannelService(db_session, bot)
    channels = await channel_service.list_user_channels(user.id)

    if not channels:
        await callback.message.edit_text(
            "📋 У вас нет каналов. Сначала добавьте канал.",
        )
        await callback.answer()
        return

    text = "📋 <b>Очередь публикаций по всем каналам</b>\n\n"
    for ch in channels:
        post_service = PostService(db_session, bot)
        queue = await post_service.list_queue(ch.id)
        text += f"📢 {ch.title}: <b>{len(queue)}</b> в очереди\n"

    await callback.message.edit_text(text)
    await callback.answer()
