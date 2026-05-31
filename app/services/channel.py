from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from aiogram.types import ChatFullInfo

from app.database.repository import BaseRepository
from app.models.channel import TelegramChannel
from app.models.user import User
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChannelService:
    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self.repo = BaseRepository(TelegramChannel, session)

    async def add_channel(self, channel_id: int, owner: User) -> TelegramChannel | None:
        existing = await self.repo.get(channel_id)
        if existing:
            return existing

        try:
            chat = await self.bot.get_chat(channel_id)
            if chat.type != "channel":
                return None

            member = await self.bot.get_chat_member(channel_id, (await self.bot.me()).id)
            if member.status not in ("administrator", "creator"):
                return None

            channel = await self.repo.create(
                id=channel_id,
                title=chat.title or "Unknown",
                username=chat.username,
                invite_link=chat.invite_link,
                owner_id=owner.id,
            )
            logger.info(f"Channel added: {channel_id} by user {owner.id}")
            return channel
        except Exception as e:
            logger.error(f"Failed to add channel {channel_id}: {e}")
            return None

    async def remove_channel(self, channel_id: int) -> bool:
        return await self.repo.delete(channel_id)

    async def get_channel(self, channel_id: int) -> TelegramChannel | None:
        return await self.repo.get(channel_id)

    async def list_user_channels(self, user_id: int) -> list[TelegramChannel]:
        return await self.repo.list(owner_id=user_id)

    async def toggle_active(self, channel_id: int) -> TelegramChannel | None:
        channel = await self.repo.get(channel_id)
        if channel is None:
            return None
        return await self.repo.update(channel_id, is_active=not channel.is_active)

    async def update_channel(self, channel_id: int, **kwargs) -> TelegramChannel | None:
        return await self.repo.update(channel_id, **kwargs)
