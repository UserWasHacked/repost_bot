from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import async_session_factory
from app.bot import bot
from app.services.publisher import PublisherService
from app.models.schedule import Schedule
from app.models.post import PostStatus
from app.utils.logger import get_logger

logger = get_logger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


async def publish_scheduled_post(post_id: int) -> None:
    async with async_session_factory() as session:
        publisher = PublisherService(session, bot)
        await publisher.publish_post(post_id)


async def publish_from_queue(channel_id: int) -> None:
    async with async_session_factory() as session:
        publisher = PublisherService(session, bot)
        await publisher.publish_queued_next(channel_id)


async def execute_schedule(schedule_id: int) -> None:
    async with async_session_factory() as session:
        from app.database.repository import BaseRepository

        schedule_repo = BaseRepository(Schedule, session)
        schedule = await schedule_repo.get(schedule_id)
        if schedule is None or not schedule.is_enabled:
            return

        publisher = PublisherService(session, bot)
        next_post = await publisher.post_service.get_next_queued(schedule.channel_id)
        if next_post is None:
            channel = await publisher.channel_repo.get(schedule.channel_id)
            if channel and channel.auto_fill_queue:
                from app.services.ai_generator import AIGeneratorService
                from app.services.post import PostService
                from app.models.post import PostType
                import random

                topics = [t.strip() for t in (schedule.ai_topic or "").split(",") if t.strip()]
                selected_topic = random.choice(topics) if topics else "life_reflection"

                ai = AIGeneratorService()
                texts = await ai.generate_post(
                    topic=selected_topic,
                    tone=schedule.ai_tone or "warm",
                    length=schedule.text_length or 200,
                    emotionality=schedule.emotionality or 5,
                    paragraphs=schedule.paragraphs or 2,
                )
                if texts and not texts[0].startswith("❌"):
                    post_service = PostService(session, bot)
                    from app.models.user import User
                    user_repo = BaseRepository(User, session)
                    owner = await user_repo.get(schedule.channel.owner_id)
                    if owner:
                        post = await post_service.create_post(
                            channel_id=schedule.channel_id,
                            author=owner,
                            text=texts[0],
                            is_ai_generated=True,
                            ai_prompt_topic=selected_topic,
                        )
                        await post_service.add_to_queue(post.id)
                        next_post = post

        if next_post:
            await publisher.publish_post(next_post.id)


class SchedulerService:
    def __init__(self):
        self.scheduler = scheduler

    def start(self) -> None:
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("APScheduler started")

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("APScheduler stopped")

    async def schedule_post(self, post_id: int, run_at: datetime) -> None:
        self.scheduler.add_job(
            publish_scheduled_post,
            trigger=DateTrigger(run_date=run_at),
            args=[post_id],
            id=f"post_{post_id}",
            replace_existing=True,
            misfire_grace_time=300,
        )
        logger.info(f"Scheduled post {post_id} at {run_at}")

    async def add_schedule_job(self, schedule: Schedule) -> None:
        job_id = f"schedule_{schedule.id}"

        if schedule.interval_hours:
            self.scheduler.add_job(
                execute_schedule,
                trigger=IntervalTrigger(hours=schedule.interval_hours),
                args=[schedule.id],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300,
            )
        elif schedule.daily and schedule.specific_time:
            self.scheduler.add_job(
                execute_schedule,
                trigger=CronTrigger(
                    hour=schedule.specific_time.hour,
                    minute=schedule.specific_time.minute,
                    timezone="UTC",
                ),
                args=[schedule.id],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300,
            )
        elif schedule.weekly and schedule.weekly_day is not None and schedule.specific_time:
            self.scheduler.add_job(
                execute_schedule,
                trigger=CronTrigger(
                    day_of_week=schedule.weekly_day,
                    hour=schedule.specific_time.hour,
                    minute=schedule.specific_time.minute,
                    timezone="UTC",
                ),
                args=[schedule.id],
                id=job_id,
                replace_existing=True,
                misfire_grace_time=300,
            )

        logger.info(f"Schedule job added for schedule {schedule.id}")

    async def remove_schedule_job(self, schedule_id: int) -> None:
        job_id = f"schedule_{schedule_id}"
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Schedule job removed for schedule {schedule_id}")

    async def load_all_schedules(self) -> None:
        async with async_session_factory() as session:
            from app.database.repository import BaseRepository

            repo = BaseRepository(Schedule, session)
            all_schedules = await repo.list()
            for s in all_schedules:
                if s.is_enabled:
                    await self.add_schedule_job(s)

    async def load_channel_schedules(self, channel_id: int) -> None:
        async with async_session_factory() as session:
            from app.database.repository import BaseRepository

            repo = BaseRepository(Schedule, session)
            schedules = await repo.list(channel_id=channel_id)
            for s in schedules:
                if s.is_enabled:
                    await self.add_schedule_job(s)
