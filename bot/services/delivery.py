"""Sending media to Telegram.

Media is always referenced **by URL** so Telegram's own servers fetch it and the
bot moves no bytes. Bytes are only downloaded as a last resort, when Telegram
refuses a URL (hotlink protection, CDN rejection, oversized asset) and
`IMAGE_FALLBACK_UPLOAD` is enabled.
"""

from __future__ import annotations

import logging

from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import BufferedInputFile, InputMediaPhoto, Message

log = logging.getLogger(__name__)

MAX_ALBUM = 10


class DeliveryOutcome:
    __slots__ = ("messages", "sent", "failed")

    def __init__(self, messages: list[Message], sent: int, failed: int):
        self.messages = messages
        self.sent = sent
        self.failed = failed

    @property
    def message_ids(self) -> list[int]:
        return [message.message_id for message in self.messages]


async def send_media_page(
    bot,
    chat_id: int,
    urls: list[str],
    *,
    caption: str | None = None,
    reply_markup=None,
    spoiler: bool = False,
    mode: str = "album",
    fallback: bool = True,
    downloader=None,
) -> DeliveryOutcome:
    """Send one gallery page.

    ``mode="album"`` posts a media group of up to 10 images (caption on the first
    item, keyboard attached afterwards by the caller); ``mode="single"`` posts one
    image so the message can be edited in place later.
    """
    urls = [url for url in dict.fromkeys(urls) if url]
    if not urls:
        return DeliveryOutcome([], 0, 0)

    if mode == "single" or len(urls) == 1:
        message = await _send_one(
            bot, chat_id, urls[0], caption=caption, reply_markup=reply_markup, spoiler=spoiler
        )
        return DeliveryOutcome([message], 1, 0)

    media = [
        InputMediaPhoto(media=url, caption=caption if index == 0 else None, has_spoiler=spoiler)
        for index, url in enumerate(urls[:MAX_ALBUM])
    ]
    try:
        messages = await bot.send_media_group(chat_id=chat_id, media=media)
        return DeliveryOutcome(list(messages), len(messages), 0)
    except TelegramBadRequest as exc:
        log.info("album by URL rejected (%s); falling back", exc)
        if not fallback:
            raise

    if downloader is None:
        return DeliveryOutcome([], 0, len(urls))

    uploaded: list[InputMediaPhoto] = []
    for index, url in enumerate(urls[:MAX_ALBUM]):
        try:
            raw = await downloader(url)
        except Exception as exc:  # noqa: BLE001 - source failures must not break the page
            log.warning("download failed for %s: %s", url, exc)
            continue
        uploaded.append(
            InputMediaPhoto(
                media=BufferedInputFile(raw, filename=f"image_{index}.jpg"),
                caption=caption if index == 0 else None,
                has_spoiler=spoiler,
            )
        )

    if not uploaded:
        return DeliveryOutcome([], 0, len(urls))
    if len(uploaded) == 1:
        message = await bot.send_photo(
            chat_id=chat_id,
            photo=uploaded[0].media,
            caption=caption,
            reply_markup=reply_markup,
            has_spoiler=spoiler,
        )
        return DeliveryOutcome([message], 1, len(urls) - 1)
    try:
        messages = await bot.send_media_group(chat_id=chat_id, media=uploaded)
        return DeliveryOutcome(list(messages), len(messages), len(urls) - len(uploaded))
    except TelegramAPIError as exc:
        log.warning("album upload failed: %s", exc)
        return DeliveryOutcome([], 0, len(urls))


async def send_preview_photo(
    bot,
    chat_id: int,
    url: str,
    *,
    caption: str | None = None,
    reply_markup=None,
    spoiler: bool = False,
) -> Message | None:
    """One photo card. Returns None when Telegram rejects the URL, so the caller can
    fall back to a text card instead of failing the whole screen."""
    try:
        return await _send_one(
            bot, chat_id, url, caption=caption, reply_markup=reply_markup, spoiler=spoiler
        )
    except TelegramAPIError as exc:
        log.info("thumbnail rejected (%s); sending text only", exc)
        return None


async def _send_one(
    bot,
    chat_id: int,
    url: str,
    *,
    caption: str | None = None,
    reply_markup=None,
    spoiler: bool = False,
) -> Message:
    return await bot.send_photo(
        chat_id=chat_id,
        photo=url,
        caption=caption,
        reply_markup=reply_markup,
        has_spoiler=spoiler,
    )


async def edit_to_photo(bot, chat_id: int, message_id: int, url: str, *, caption: str, reply_markup=None) -> None:
    """In-place single-image paging (delivery_mode = single)."""
    await bot.edit_message_media(
        chat_id=chat_id,
        message_id=message_id,
        media=InputMediaPhoto(media=url, caption=caption),
        reply_markup=reply_markup,
    )