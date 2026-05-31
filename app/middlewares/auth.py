from typing import Callable, Awaitable, Any
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery

from app.config import settings
from app.database.session import async_session_factory
from app.database.repository import BaseRepository
from app.models.user import User


class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user_event = None
        if isinstance(event, Message):
            user_event = event
        elif isinstance(event, CallbackQuery):
            user_event = event

        if user_event and user_event.from_user:
            tg_user = user_event.from_user
            async with async_session_factory() as session:
                repo = BaseRepository(User, session)
                user = await repo.get(tg_user.id)
                if user is None:
                    user = await repo.create(
                        id=tg_user.id,
                        username=tg_user.username,
                        first_name=tg_user.first_name,
                        last_name=tg_user.last_name,
                        is_admin=tg_user.id in settings.admin_ids,
                    )
                elif not user.is_active:
                    return
                data["user"] = user
                data["db_session"] = session

        return await handler(event, data)
