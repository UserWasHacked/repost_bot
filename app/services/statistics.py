from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timezone, timedelta

from app.database.repository import BaseRepository
from app.models.post import Post, PostStatus
from app.models.channel import TelegramChannel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class StatisticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.post_repo = BaseRepository(Post, session)
        self.channel_repo = BaseRepository(TelegramChannel, session)

    async def get_channel_stats(self, channel_id: int) -> dict:
        posts = await self.post_repo.list(channel_id=channel_id)
        total = len(posts)
        published = len([p for p in posts if p.status == PostStatus.published])
        scheduled = len([p for p in posts if p.status == PostStatus.scheduled])
        queued = len([p for p in posts if p.status == PostStatus.queued])
        drafts = len([p for p in posts if p.status == PostStatus.draft])
        failed = len([p for p in posts if p.status == PostStatus.failed])

        ai_count = len([p for p in posts if p.is_ai_generated])

        now = datetime.now(timezone.utc)
        today = len([p for p in posts if p.published_at and p.published_at.date() == now.date()])
        this_week = len(
            [
                p
                for p in posts
                if p.published_at and p.published_at >= now - timedelta(days=7)
            ]
        )

        return {
            "total": total,
            "published": published,
            "scheduled": scheduled,
            "queued": queued,
            "drafts": drafts,
            "failed": failed,
            "ai_generated": ai_count,
            "today": today,
            "this_week": this_week,
        }

    async def get_user_stats(self, user_id: int) -> dict:
        channels = await self.channel_repo.list(owner_id=user_id)
        channel_count = len(channels)

        total_posts = 0
        total_published = 0
        for ch in channels:
            posts = await self.post_repo.list(channel_id=ch.id)
            total_posts += len(posts)
            total_published += len([p for p in posts if p.status == PostStatus.published])

        return {
            "channel_count": channel_count,
            "total_posts": total_posts,
            "total_published": total_published,
        }

    async def get_queue_stats(self, channel_id: int) -> dict:
        posts = await self.post_repo.list(channel_id=channel_id)
        queued = [p for p in posts if p.status == PostStatus.queued]
        scheduled = [p for p in posts if p.status == PostStatus.scheduled]

        next_post = None
        if queued:
            queued.sort(key=lambda p: p.queue_order or 0)
            next_post = queued[0]

        return {
            "queued_count": len(queued),
            "scheduled_count": len(scheduled),
            "next_post": next_post,
        }
