"""Time helpers. Everything is naive-UTC so SQLite round-trips cleanly."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def in_minutes(minutes: int) -> datetime:
    return utcnow() + timedelta(minutes=minutes)


def format_dt(value: datetime | None, *, with_time: bool = True) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M" if with_time else "%Y-%m-%d")


def humanize(value: datetime | None) -> str:
    if value is None:
        return "never"
    delta = utcnow() - value
    seconds = max(int(delta.total_seconds()), 0)
    if seconds < 60:
        return "just now"
    if seconds < 3600:
        return f"{seconds // 60} min ago"
    if seconds < 86400:
        return f"{seconds // 3600} h ago"
    days = seconds // 86400
    if days < 30:
        return f"{days} d ago"
    return format_dt(value, with_time=False)


def humanize_uptime(started: datetime) -> str:
    seconds = max(int((utcnow() - started).total_seconds()), 0)
    days, rem = divmod(seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes = rem // 60
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours or days:
        parts.append(f"{hours:02d}h")
    parts.append(f"{minutes:02d}m")
    return " ".join(parts)


def parse_span(raw: str) -> timedelta | None:
    """Parse a compact duration such as ``30m``, ``12h``, ``7d``."""
    raw = raw.strip().lower()
    if len(raw) < 2 or not raw[:-1].isdigit():
        return None
    unit = raw[-1]
    amount = int(raw[:-1])
    if amount <= 0:
        return None
    factor = {"m": 60, "h": 3600, "d": 86400}.get(unit)
    if factor is None:
        return None
    return timedelta(seconds=amount * factor)