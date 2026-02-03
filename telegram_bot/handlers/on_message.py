"""Message handlers (non-command)."""
from telegram import Update
from telegram.ext import ContextTypes

from ..services import xp_service


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        return
    if not update.message or not update.message.text:
        return
    if update.message.text.startswith("/"):
        return

    await xp_service.award_message_xp(user.id)
