from datetime import datetime, time, timedelta, timezone
import random


def parse_time_string(time_str: str) -> time | None:
    try:
        parts = time_str.strip().split(":")
        if len(parts) == 2:
            return time(hour=int(parts[0]), minute=int(parts[1]))
        return None
    except (ValueError, IndexError):
        return None


def format_datetime(dt: datetime | None, fmt: str = "%d.%m.%Y %H:%M") -> str:
    if dt is None:
        return "—"
    return dt.strftime(fmt)


def calculate_next_interval(interval_hours: float) -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=interval_hours)


def generate_queue_order(posts_count: int) -> int:
    return posts_count + 1


def mask_channel_id(channel_id: int) -> str:
    return str(channel_id)


AI_TOPICS = [
    "morning_greeting",
    "night_greeting",
    "support",
    "gratitude",
    "thinking_of_you",
    "life_reflection",
    "trust",
    "affection",
    "memories",
    "communication_value",
]

AI_TOPICS_RU = {
    "morning_greeting": "Доброе утро",
    "night_greeting": "Спокойной ночи",
    "support": "Поддержка",
    "gratitude": "Благодарность",
    "thinking_of_you": "Мысли о человеке",
    "life_reflection": "Жизненные размышления",
    "trust": "Доверие",
    "affection": "Привязанность",
    "memories": "Воспоминания",
    "communication_value": "Ценность общения",
}


def truncate_text(text: str, max_length: int = 4096) -> str:
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
