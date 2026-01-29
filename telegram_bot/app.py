"""Application setup and entrypoint for the Telegram bot."""
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

from .handlers import core as core_handlers
from .handlers import weather as weather_handlers
from .services import weather_service
from telegram.ext import CallbackQueryHandler
from .services import xp_service


def build_app():
    load_dotenv()
    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN not set in environment")

    app = ApplicationBuilder().token(token).build()

    # register handlers
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
    # message handler for awarding XP on normal messages (non-commands)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, core_handlers.on_message))
    # Weather handlers
    app.add_handler(CommandHandler("weather", weather_handlers.weather_cmd))
    app.add_handler(CallbackQueryHandler(weather_handlers.button_handler))
    # Text handler for adding locations (when waiting_for_location is set)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, weather_handlers.add_location))

    # start XP background flush task (started in main)

    return app


def main() -> None:
    app = build_app()
    print("봇을 시작합니다. 중지하려면 Ctrl-C를 누르세요.")
    
    # Callback when app starts (after event loop is running)
    async def post_init_cb(app):
        """Called after application starts, before it begins handling updates."""
        app._xp_task = app.create_task(xp_service.start_background_flush(interval_seconds=2.0))
        print("XP background flush task started.")
    
    app.post_init = post_init_cb
    
    try:
        app.run_polling()
    finally:
        # flush pending xp on shutdown
        import asyncio as _asyncio
        try:
            _asyncio.get_event_loop().run_until_complete(xp_service.flush_pending())
        except Exception:
            # last resort: run in a new loop
            _asyncio.run(xp_service.flush_pending())
        # cancel background task
        # Close weather client gracefully
        try:
            _asyncio.get_event_loop().run_until_complete(weather_service.close_client())
        except Exception:
            try:
                _asyncio.run(weather_service.close_client())
            except Exception:
                pass

        if getattr(app, "_xp_task", None):
            try:
                app._xp_task.cancel()
            except Exception:
                pass
