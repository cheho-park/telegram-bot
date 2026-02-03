"""Telegram-specific helpers for handlers."""
from __future__ import annotations

import asyncio
from telegram import Update
from telegram.ext import ContextTypes


async def send_temporary_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    text: str,
    ttl: float = None,
    **kwargs,
):
    """Send a message. If ttl is provided, delete it after `ttl` seconds.

    Returns the sent message object. `kwargs` are passed to `reply_text` (e.g., parse_mode, reply_markup).
    """
    if getattr(update, "message", None):
        sent = await update.message.reply_text(text, **kwargs)
    else:
        chat_id = update.effective_chat.id if update.effective_chat else None
        if chat_id is None:
            return None
        sent = await context.bot.send_message(chat_id=chat_id, text=text, **kwargs)

    if ttl is None:
        return sent

    async def _del_later(msg, delay: float):
        try:
            await asyncio.sleep(delay)
            try:
                await msg.delete()
            except Exception:
                pass
        except Exception:
            pass

    try:
        asyncio.create_task(_del_later(sent, float(ttl)))
    except RuntimeError:
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(_del_later(sent, float(ttl)))
        except Exception:
            pass

    return sent
