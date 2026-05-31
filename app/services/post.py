from sqlalchemy.ext.asyncio import AsyncSession
from aiogram import Bot
from datetime import datetime, timezone
from typing import Optional

from app.database.repository import BaseRepository
from app.models.post import Post, PostStatus, PostType
from app.models.user import User
from app.utils.logger import get_logger
from app.utils.helpers import generate_queue_order

logger = get_logger(__name__)


class PostService:
    def __init__(self, session: AsyncSession, bot: Bot):
        self.session = session
        self.bot = bot
        self.repo = BaseRepository(Post, session)

    async def create_post(
        self,
        channel_id: int,
        author: User,
        text: Optional[str] = None,
        post_type: PostType = PostType.text,
        media_file_ids: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        is_ai_generated: bool = False,
        ai_prompt_topic: Optional[str] = None,
    ) -> Post:
        queue_order = None
        status = PostStatus.draft

        if scheduled_at:
            status = PostStatus.scheduled

        return await self.repo.create(
            channel_id=channel_id,
            author_id=author.id,
            text=text,
            status=status,
            post_type=post_type,
            media_file_ids=media_file_ids,
            scheduled_at=scheduled_at,
            queue_order=queue_order,
            is_ai_generated=is_ai_generated,
            ai_prompt_topic=ai_prompt_topic,
        )

    async def add_to_queue(self, post_id: int) -> Post | None:
        post = await self.repo.get(post_id)
        if post is None:
            return None

        existing_queue = await self.repo.list(channel_id=post.channel_id, status=PostStatus.queued)
        max_order = max((p.queue_order or 0) for p in existing_queue) if existing_queue else 0

        return await self.repo.update(
            post_id,
            status=PostStatus.queued,
            queue_order=max_order + 1,
        )

    async def publish_post(self, post_id: int) -> Post | None:
        post = await self.repo.get(post_id)
        if post is None:
            return None

        return await self.repo.update(
            post_id,
            status=PostStatus.published,
            published_at=datetime.now(timezone.utc),
        )

    async def mark_failed(self, post_id: int, error: str) -> Post | None:
        return await self.repo.update(
            post_id,
            status=PostStatus.failed,
            error_message=error,
        )

    async def get_post(self, post_id: int) -> Post | None:
        return await self.repo.get(post_id)

    async def list_channel_posts(
        self, channel_id: int, status: Optional[PostStatus] = None, limit: int = 50
    ) -> list[Post]:
        if status:
            return await self.repo.list(channel_id=channel_id, status=status)
        all_posts = await self.repo.list(channel_id=channel_id)
        return all_posts[:limit]

    async def list_queue(self, channel_id: int) -> list[Post]:
        posts = await self.repo.list(channel_id=channel_id, status=PostStatus.queued)
        posts.sort(key=lambda p: (p.queue_order or 0))
        return posts

    async def update_post(self, post_id: int, **kwargs) -> Post | None:
        return await self.repo.update(post_id, **kwargs)

    async def delete_post(self, post_id: int) -> bool:
        return await self.repo.delete(post_id)

    async def get_next_queued(self, channel_id: int) -> Post | None:
        posts = await self.list_queue(channel_id)
        return posts[0] if posts else None

    async def get_recent_posts_count(self, channel_id: int, limit: int = 500) -> list[Post]:
        posts = await self.repo.list(channel_id=channel_id)
        published = [p for p in posts if p.status == PostStatus.published]
        published.sort(key=lambda p: p.published_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
        return published[:limit]

    async def reorder_queue(self, channel_id: int, post_ids: list[int]) -> None:
        for order, pid in enumerate(post_ids, start=1):
            await self.repo.update(pid, queue_order=order)
