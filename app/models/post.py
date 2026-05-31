from sqlalchemy import String, Text, BigInteger, Boolean, ForeignKey, Integer, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
import enum

from app.database.base import Base, TimestampMixin


class PostStatus(str, enum.Enum):
    draft = "draft"
    scheduled = "scheduled"
    queued = "queued"
    published = "published"
    failed = "failed"


class PostType(str, enum.Enum):
    text = "text"
    image = "image"
    multi_image = "multi_image"


class Post(Base, TimestampMixin):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("telegram_channels.id"), nullable=False)
    author_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)

    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PostStatus] = mapped_column(SAEnum(PostStatus), default=PostStatus.draft)
    post_type: Mapped[PostType] = mapped_column(SAEnum(PostType), default=PostType.text)

    media_file_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    media_group_id: Mapped[str | None] = mapped_column(String(256), nullable=True)

    scheduled_at: Mapped[datetime | None] = mapped_column(nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
    queue_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    ai_prompt_topic: Mapped[str | None] = mapped_column(String(256), nullable=True)

    telegram_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    views_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    channel = relationship("TelegramChannel", back_populates="posts")
    author = relationship("User", back_populates="posts")
