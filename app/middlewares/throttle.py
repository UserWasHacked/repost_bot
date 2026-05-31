from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware, Dispatcher
from aiogram.types import TelegramObject, Message, CallbackQuery
from aiogram.exceptions import TelegramRetryAfter
from collections import defaultdict
import time
import asyncio

from app.utils.logger import get_logger

logger = get_logger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate_limit: float = 0.5):
        self.rate_limit = rate_limit
        self.last_time = defaultdict(float)

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("user")
        if user:
            now = time.time()
            user_id = user.id
            if now - self.last_time[user_id] < self.rate_limit:
                return
            self.last_time[user_id] = now

        try:
            return await handler(event, data)
        except TelegramRetryAfter as e:
            logger.warning(f"Rate limited, waiting {e.retry_after}s")
            await asyncio.sleep(e.retry_after)
            return await handler(event, data)
