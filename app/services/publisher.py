from aiogram import Bot
from aiogram.types import InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Optional

from app.database.repository import BaseRepository
from app.models.post import Post, PostStatus, PostType
from app.models.channel import TelegramChannel
from app.services.post import PostService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class PublisherService:
    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self.post_service = PostService(session, bot)
        self.channel_repo = BaseRepository(TelegramChannel, session)

    async def publish_post(self, post_id: int) -> bool:
        post = await self.post_service.get_post(post_id)
        if post is None:
            return False

        channel = await self.channel_repo.get(post.channel_id)
        if channel is None:
            return False

        try:
            message_id = None

            if post.post_type == PostType.text:
                msg = await self.bot.send_message(
                    chat_id=channel.id,
                    text=post.text or "",
                )
                message_id = msg.message_id

            elif post.post_type == PostType.image and post.media_file_ids:
                file_ids = post.media_file_ids.split("|")
                msg = await self.bot.send_photo(
                    chat_id=channel.id,
                    photo=file_ids[0],
                    caption=post.text or "",
                )
                message_id = msg.message_id

            elif post.post_type == PostType.multi_image and post.media_file_ids:
                file_ids = post.media_file_ids.split("|")
                media_group = [
                    InputMediaPhoto(media=fid, caption=post.text if i == 0 else None)
                    for i, fid in enumerate(file_ids)
                ]
                msgs = await self.bot.send_media_group(
                    chat_id=channel.id,
                    media=media_group,
                )
                if msgs:
                    message_id = msgs[0].message_id

            await self.post_service.update_post(
                post_id,
                status=PostStatus.published,
                published_at=datetime.now(timezone.utc),
                telegram_message_id=message_id,
            )

            await self.channel_repo.update(channel.id, last_posted_at=datetime.now(timezone.utc))

            logger.info(f"Post {post_id} published to channel {channel.id}")
            return True

        except Exception as e:
            logger.error(f"Failed to publish post {post_id}: {e}")
            await self.post_service.mark_failed(post_id, str(e))
            return False

    async def publish_queued_next(self, channel_id: int) -> bool:
        next_post = await self.post_service.get_next_queued(channel_id)
        if next_post is None:
            return False
        return await self.publish_post(next_post.id)

    async def send_preview(self, post_id: int, chat_id: int) -> bool:
        post = await self.post_service.get_post(post_id)
        if post is None:
            return False

        try:
            if post.post_type == PostType.text:
                await self.bot.send_message(chat_id=chat_id, text=post.text or "")
            elif post.post_type == PostType.image and post.media_file_ids:
                file_ids = post.media_file_ids.split("|")
                await self.bot.send_photo(
                    chat_id=chat_id, photo=file_ids[0], caption=post.text or ""
                )
            elif post.post_type == PostType.multi_image and post.media_file_ids:
                file_ids = post.media_file_ids.split("|")
                media_group = [
                    InputMediaPhoto(media=fid, caption=post.text if i == 0 else None)
                    for i, fid in enumerate(file_ids)
                ]
                await self.bot.send_media_group(chat_id=chat_id, media=media_group)
            return True
        except Exception as e:
            logger.error(f"Preview failed for post {post_id}: {e}")
            return False
