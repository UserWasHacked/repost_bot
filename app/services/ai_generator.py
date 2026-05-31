from openai import AsyncOpenAI, APIStatusError
from typing import Optional
import asyncio

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

AI_TOPIC_PROMPTS = {
    "morning_greeting": (
        "Напиши теплое утреннее приветствие для близкого человека. "
        "Оно должно звучать как личное сообщение, без шаблонов и клише."
    ),
    "night_greeting": (
        "Напиши нежное сообщение на ночь для близкого человека. "
        "Спокойное, уютное, без романтизации."
    ),
    "support": (
        "Напиши поддерживающее сообщение для человека, который проходит через сложный период. "
        "Тепло, искренне, без советов и наставлений."
    ),
    "gratitude": (
        "Напиши сообщение с благодарностью близкому человеку. "
        "Искренне, за что-то конкретное или просто так."
    ),
    "thinking_of_you": (
        "Напиши сообщение о том, что ты думаешь о человеке. "
        "Теплое, легкое, без навязчивости."
    ),
    "life_reflection": (
        "Напиши короткое жизненное размышление. "
        "О простых вещах, о течении жизни, о людях рядом."
    ),
    "trust": (
        "Напиши сообщение о доверии между людьми. "
        "О том, как важно иметь кого-то, кому можно доверять."
    ),
    "affection": (
        "Напиши сообщение о привязанности к человеку. "
        "Теплое, без чрезмерной романтизации, естественное."
    ),
    "memories": (
        "Напиши сообщение-воспоминание. "
        "О каком-то приятном моменте, разделенном с человеком."
    ),
    "communication_value": (
        "Напиши о ценности общения с конкретным человеком. "
        "О том, как важны разговоры и тишина между ними."
    ),
}


class AIGeneratorService:
    def __init__(self):
        self.client = None
        if settings.gemini_api_key:
            self.client = AsyncOpenAI(
                api_key=settings.gemini_api_key,
                base_url=GEMINI_BASE_URL,
            )
        self.model = settings.gemini_model

    async def generate_post(
        self,
        topic: str,
        tone: str = "warm",
        length: int = 200,
        emotionality: int = 5,
        paragraphs: int = 2,
        exclude_recent: Optional[list[str]] = None,
        variants: int = 1,
    ) -> list[str]:
        if self.client is None:
            return ["❌ Gemini API не настроен. Укажите GEMINI_API_KEY в .env"]

        topic_prompt = AI_TOPIC_PROMPTS.get(topic, "Напиши теплое личное сообщение.")

        system_prompt = (
            "Ты профессиональный автор текстов для Telegram-канала с тематикой искренних чувств, "
            "человеческих отношений, привязанности, поддержки, мыслей перед сном и утренней мотивации.\n\n"
            "Твоя задача — создавать уникальные тексты, которые выглядят как личное сообщение "
            "от одного человека другому.\n\n"
            "Требования к стилю:\n"
            "- Пиши естественно и по-человечески\n"
            "- Избегай чрезмерной романтизации, пафоса и приторной нежности\n"
            "- Не используй уменьшительно-ласкательные обращения\n"
            "- Не используй шаблонные фразы из открыток и статусов\n"
            "- Основной акцент на искренности, честности и эмоциональной близости\n"
            "- Тексты должны вызывать ощущение настоящего общения\n"
            "- Используй спокойный, теплый и взрослый тон\n"
            "- Без эмодзи\n"
            "- Каждый текст уникален, не повторяйся\n"
            "- Не повторяй предложения и смысловые конструкции из предыдущих публикаций\n"
            f"- Объем текста: от 120 до 250 слов (сейчас ~{length} символов)\n"
            f"- Количество абзацев: примерно {paragraphs}\n"
            "- Пиши от первого лица (я)\n"
            "- Не используй обращения по имени\n\n"
            "При генерации случайным образом меняй:\n"
            "- длину абзацев\n"
            "- структуру текста\n"
            "- эмоциональную глубину\n"
            "- начало и завершение текста\n\n"
            "Каждый пост должен ощущаться как отдельная история, а не как вариация предыдущего текста.\n"
            "Если указана тема — строго придерживайся темы.\n"
            "Формат ответа: только готовый текст для публикации без заголовков, пояснений и служебной информации."
        )

        if exclude_recent:
            system_prompt += (
                "\n\nИзбегай следующих тем и фраз, так как они уже были использованы недавно:\n"
                + "\n".join(f"- {text[:100]}" for text in exclude_recent)
            )

        user_prompt = (
            f"Тема: {topic_prompt}\n"
            f"Тональность: {tone}\n"
            f"Напиши {variants} вариант(а) текста. "
            "Каждый вариант отделяй строкой '---VARIANT---'."
        )

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.8 + (emotionality - 5) * 0.05,
                    max_tokens=2000,
                )

                content = response.choices[0].message.content or ""
                finish = response.choices[0].finish_reason
                if finish == "length":
                    logger.warning("AI response was truncated (finish_reason=length)")
                texts = [t.strip() for t in content.split("---VARIANT---") if t.strip()]
                return texts if texts else [content]

            except APIStatusError as e:
                if e.status_code == 429 and attempt < max_retries - 1:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Rate limited (429), retrying in {wait}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait)
                    continue
                logger.error(f"Gemini API error ({e.status_code}): {e}")
                return [f"❌ Ошибка Gemini API: {e.status_code}. Попробуйте позже."]
            except Exception as e:
                logger.error(f"AI generation failed: {e}")
                return [f"❌ Ошибка генерации: {e}"]

        return ["❌ Превышено количество попыток. Попробуйте позже."]
