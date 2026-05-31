import asyncio
import sys

from aiogram import Router
from aiogram.types import ErrorEvent
from aiogram.exceptions import TelegramBadRequest

from app.bot import bot, dp
from app.config import settings
from app.database.base import Base
from app.database.session import engine
from app.handlers.start import router as start_router
from app.handlers.channels import router as channels_router
from app.handlers.posts import router as posts_router
from app.handlers.schedule_handler import router as schedule_router
from app.handlers.generation import router as generation_router
from app.handlers.admin import router as admin_router
from app.middlewares.auth import AuthMiddleware
from app.middlewares.logging import LoggingMiddleware
from app.middlewares.throttle import ThrottlingMiddleware
from app.services.scheduler import SchedulerService
from app.utils.logger import setup_logging, get_logger

errors_router = Router()


@errors_router.errors()
async def handle_error(event: ErrorEvent):
    if isinstance(event.exception, TelegramBadRequest) and "message is not modified" in str(event.exception):
        return
    logger = get_logger(__name__)
    logger.error(f"Unhandled error: {event.exception}")

logger = get_logger(__name__)


async def on_startup() -> None:
    logger.info("Starting bot...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    scheduler_service = SchedulerService()
    await scheduler_service.load_all_schedules()
    scheduler_service.start()

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info(f"Bot started as @{(await bot.me()).username}")


async def on_shutdown() -> None:
    logger.info("Shutting down bot...")
    scheduler_service = SchedulerService()
    scheduler_service.stop()
    await bot.session.close()
    await engine.dispose()
    logger.info("Bot stopped")


async def main() -> None:
    setup_logging()

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    dp.message.middleware(LoggingMiddleware())
    dp.callback_query.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    dp.include_router(errors_router)
    dp.include_router(start_router)
    dp.include_router(channels_router)
    dp.include_router(posts_router)
    dp.include_router(schedule_router)
    dp.include_router(generation_router)
    dp.include_router(admin_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
