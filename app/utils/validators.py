import re


CHANNEL_LINK_PATTERN = re.compile(r"^(https?://)?t\.me/([a-zA-Z0-9_]+)$")
CHANNEL_ID_PATTERN = re.compile(r"^-100\d+$")


def validate_channel_link(link: str) -> str | None:
    match = CHANNEL_LINK_PATTERN.match(link.strip())
    if match:
        return match.group(2)
    return None


def validate_channel_id(channel_id: str) -> bool:
    return bool(CHANNEL_ID_PATTERN.match(channel_id.strip()))


def validate_interval(interval_str: str) -> float | None:
    try:
        value = float(interval_str)
        if 0.1 <= value <= 720:
            return value
        return None
    except ValueError:
        return None


def validate_time(time_str: str) -> str | None:
    try:
        parts = time_str.strip().split(":")
        if len(parts) != 2:
            return None
        hours, minutes = int(parts[0]), int(parts[1])
        if 0 <= hours <= 23 and 0 <= minutes <= 59:
            return f"{hours:02d}:{minutes:02d}"
        return None
    except (ValueError, IndexError):
        return None


def validate_positive_int(value: str, max_val: int = 1000) -> int | None:
    try:
        v = int(value)
        if 1 <= v <= max_val:
            return v
        return None
    except ValueError:
        return None
