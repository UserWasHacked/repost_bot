from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.utils.logger import get_logger

logger = get_logger(__name__)


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("user")
        user_str = f"user={user.id}" if user else "user=unknown"

        if isinstance(event, Message):
            text = event.text or event.caption or "[media]"
            logger.info(f"[{user_str}] message: {text[:200]}")
        elif isinstance(event, CallbackQuery):
            logger.info(f"[{user_str}] callback: {event.data}")

        return await handler(event, data)
