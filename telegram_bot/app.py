"""Application setup and entrypoint for the Telegram bot."""

import os
import asyncio
from dotenv import load_dotenv

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from .handlers import core as core_handlers
from .handlers import weather as weather_handlers
from .services import xp_service
from .services import weather_service


def build_app():
    """Build and configure the Telegram Application."""
    load_dotenv()

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment")

    app = ApplicationBuilder().token(token).build()

    # Core command handlers
    app.add_handler(CommandHandler("start", core_handlers.start))
    app.add_handler(CommandHandler("help", core_handlers.help_command))
    app.add_handler(CommandHandler("ping", core_handlers.ping))
    app.add_handler(CommandHandler("register", core_handlers.register))
    app.add_handler(CommandHandler("me", core_handlers.me))
    app.add_handler(CommandHandler("attend", core_handlers.attend))
    app.add_handler(CommandHandler("attendance", core_handlers.attendance))
    app.add_handler(CommandHandler("streak", core_handlers.streak))
    app.add_handler(CommandHandler("xp", core_handlers.xp))
    app.add_handler(CommandHandler("leaderboard", core_handlers.leaderboard))

    # XP awarding for normal messages
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, core_handlers.on_message)
    )

    # Weather handlers
    app.add_handler(CommandHandler("weather", weather_handlers.weather_cmd))
    app.add_handler(CallbackQueryHandler(weather_handlers.button_handler))
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, weather_handlers.add_location)
    )

    return app


async def post_init_cb(app):
    """Called after the application starts and the event loop is running."""
    xp_task = app.create_task(
        xp_service.start_background_flush(interval_seconds=2.0)
    )

    # Store task reference in an officially supported container
    app.bot_data["xp_task"] = xp_task


async def post_shutdown_cb(app):
    """Gracefully shut down background tasks and services."""
    # Cancel XP background task
    xp_task = app.bot_data.get("xp_task")
    if xp_task:
        xp_task.cancel()
        try:
            await xp_task
        except asyncio.CancelledError:
            pass

    # Flush remaining XP data
    await xp_service.flush_pending()

    # Close weather service resources
    await weather_service.close_client()


def main() -> None:
    """Application entrypoint."""
    app = build_app()

    app.post_init = post_init_cb
    app.post_shutdown = post_shutdown_cb

    print("봇을 시작합니다. 중지하려면 Ctrl-C를 누르세요.")
    app.run_polling()
