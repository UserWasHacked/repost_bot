from sqlalchemy import String, BigInteger, Boolean, Float, ForeignKey, Integer, Time, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import time

from app.database.base import Base, TimestampMixin


class Schedule(Base, TimestampMixin):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_channels.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(256), default="Default")

    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    interval_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    specific_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    daily: Mapped[bool] = mapped_column(Boolean, default=False)
    weekly: Mapped[bool] = mapped_column(Boolean, default=False)
    weekly_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    post_type: Mapped[str] = mapped_column(String(64), default="text")

    ai_generated: Mapped[bool] = mapped_column(Boolean, default=True)
    ai_topic: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ai_tone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    text_length: Mapped[int | None] = mapped_column(Integer, default=200)
    emotionality: Mapped[int | None] = mapped_column(Integer, default=5)
    paragraphs: Mapped[int | None] = mapped_column(Integer, default=2)

    channel = relationship("TelegramChannel", back_populates="schedules")
