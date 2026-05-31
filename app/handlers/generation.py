from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from app.keyboards.schedule import ai_topic_keyboard
from app.keyboards.posts import publish_now_or_schedule_keyboard
from app.services.ai_generator import AIGeneratorService
from app.services.post import PostService
from app.models.post import PostType, PostStatus
from app.utils.logger import get_logger
from app.utils.helpers import AI_TOPICS_RU

router = Router()
logger = get_logger(__name__)


class AIGenerationState(StatesGroup):
    waiting_for_topic = State()
    waiting_for_variant = State()


@router.callback_query(F.data.startswith("post:ai:"))
async def ai_generation_start(callback: CallbackQuery, state: FSMContext):
    channel_id = int(callback.data.split(":")[2])
    await state.update_data(channel_id=channel_id)

    await callback.message.edit_text(
        "🤖 <b>Генерация текста через ИИ</b>\n\n"
        "Выберите тему для поста:",
        reply_markup=ai_topic_keyboard(channel_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("ai:topic:"))
async def ai_topic_selected(callback: CallbackQuery, user, db_session, state: FSMContext):
    parts = callback.data.split(":")
    channel_id = int(parts[2])
    topic = parts[3]

    await state.update_data(topic=topic, channel_id=channel_id)

    await callback.message.edit_text(
        f"🤖 Выбрана тема: <b>{AI_TOPICS_RU.get(topic, topic)}</b>\n\n"
        "Генерирую варианты... ⏳"
    )
    await callback.answer()

    ai_service = AIGeneratorService()

    post_service = PostService(db_session, callback.bot)
    recent_posts = await post_service.get_recent_posts_count(channel_id, limit=500)
    recent_texts = [p.text for p in recent_posts if p.text][:20]

    texts = await ai_service.generate_post(
        topic=topic,
        variants=3,
        exclude_recent=recent_texts if recent_texts else None,
    )

    if not texts:
        await callback.message.edit_text("❌ Не удалось сгенерировать текст. Попробуйте позже.")
        return

    await state.update_data(texts=texts, current_variant=0)

    first_text = texts[0][:200] + "..." if len(texts[0]) > 200 else texts[0]
    variants_text = ""
    for i, t in enumerate(texts, 1):
        preview = t[:100].replace("\n", " ") + "..."
        variants_text += f"\n<b>Вариант {i}:</b> {preview}"

    await callback.message.edit_text(
        f"✅ <b>Сгенерировано {len(texts)} вариантов:</b>\n{variants_text}\n\n"
        "✏️ Отправьте номер варианта (1-3), который хотите использовать,\n"
        "или отправьте «ещё» для генерации новых вариантов.",
    )
    await state.set_state(AIGenerationState.waiting_for_variant)


@router.message(AIGenerationState.waiting_for_variant)
async def ai_variant_selected(message: Message, user, db_session, state: FSMContext):
    data = await state.get_data()
    texts = data.get("texts", [])
    channel_id = data["channel_id"]
    topic = data.get("topic", "life_reflection")
    choice = message.text.strip().lower()

    if choice == "ещё":
        await message.answer("Генерирую новые варианты... ⏳")

        ai_service = AIGeneratorService()
        post_service = PostService(db_session, message.bot)
        recent_posts = await post_service.get_recent_posts_count(channel_id, limit=500)
        recent_texts = [p.text for p in recent_posts if p.text][:20]

        new_texts = await ai_service.generate_post(
            topic=topic,
            variants=3,
            exclude_recent=recent_texts if recent_texts else None,
        )

        if not new_texts:
            await message.answer("❌ Ошибка генерации. Попробуйте позже.")
            return

        await state.update_data(texts=new_texts, current_variant=0)

        variants_text = ""
        for i, t in enumerate(new_texts, 1):
            preview = t[:100].replace("\n", " ") + "..."
            variants_text += f"\n<b>Вариант {i}:</b> {preview}"

        await message.answer(
            f"✅ <b>Новые варианты:</b>\n{variants_text}\n\n"
            "✏️ Отправьте номер варианта (1-3):"
        )
        return

    try:
        variant_num = int(choice)
        if variant_num < 1 or variant_num > len(texts):
            raise ValueError
    except ValueError:
        await message.answer("❌ Отправьте номер (1-3) или «ещё».")
        return

    selected_text = texts[variant_num - 1]

    post_service = PostService(db_session, message.bot)
    post = await post_service.create_post(
        channel_id=channel_id,
        author=user,
        text=selected_text,
        post_type=PostType.text,
        is_ai_generated=True,
        ai_prompt_topic=topic,
    )

    await message.answer(
        f"✅ Пост сгенерирован ИИ!\n\n{selected_text}",
        reply_markup=publish_now_or_schedule_keyboard(post.id),
    )
    await state.clear()
