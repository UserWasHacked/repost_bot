from sqlalchemy import String, BigInteger, Boolean, Float, ForeignKey, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import time, datetime

from app.database.base import Base, TimestampMixin


class TelegramChannel(Base, TimestampMixin):
    __tablename__ = "telegram_channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    username: Mapped[str | None] = mapped_column(String(256), nullable=True)
    invite_link: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    owner_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    schedule_interval_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    schedule_time: Mapped[time | None] = mapped_column(nullable=True)
    schedule_daily: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_weekly: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_weekly_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    auto_fill_queue: Mapped[bool] = mapped_column(Boolean, default=False)
    queue_min_posts: Mapped[int] = mapped_column(Integer, default=10)

    allow_ai_generation: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_tone: Mapped[str] = mapped_column(String(64), default="warm")

    last_posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    next_post_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    owner = relationship("User", back_populates="channels")
    posts = relationship("Post", back_populates="channel", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="channel", cascade="all, delete-orphan")
