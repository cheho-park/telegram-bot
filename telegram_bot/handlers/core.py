"""Core handlers: thin Telegram-facing endpoints only."""
from telegram import Update
from telegram.ext import ContextTypes

from ..utils import extract_ttl_from_args
from .telegram_utils import send_temporary_message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args)  # pyright: ignore[reportArgumentType]
    await send_temporary_message(
        update,
        context,
        "안녕하세요! 봇 뼈대입니다. /help로 도움말 확인하세요.",
        ttl=ttl, # pyright: ignore[reportArgumentType]
    )
    try:
        await update.message.delete() # pyright: ignore[reportOptionalMemberAccess]
    except Exception:
        pass


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args) # pyright: ignore[reportArgumentType]
    text = (
        "🏁 /start — 시작\n"
        "❓ /help — 도움말\n"
        "🏓 /ping — 응답 확인\n"
        "📝 /register — 등록\n"
        "👤 /me — 내 정보\n"
        "🌦️ /weather — 실시간 날씨 확인\n"
        "🔮 /fortune [random] — 오늘의 운세 (random: 랜덤 운세)\n"
        "📅 /attend — 출석 체크 (하루 1회)\n"
        "📋 /attendance [n] — 내 출석 기록 조회 (최근 n개)\n"
        "🔥 /streak — 연속 출석일수 조회\n"
        "⭐ /xp — 내 XP 및 레벨 조회\n"
        "🏆 /leaderboard [n] — XP 기준 상위 n명 확인\n"
        "\n"
        "💬 메시지 자동 삭제\n"
        "• 사용자 명령: 자동으로 즉시 삭제\n"
        "• 봇 응답: 기본 유지 (ttl:시간 으로 선택 삭제)\n"
        "예: /help ttl:5 → 5초 후 삭제\n"
    )
    await send_temporary_message(update, context, text, ttl=ttl) # pyright: ignore[reportArgumentType]
    try:
        await update.message.delete() # pyright: ignore[reportOptionalMemberAccess]
    except Exception:
        pass


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args) # pyright: ignore[reportArgumentType]
    await send_temporary_message(update, context, "pong", ttl=ttl) # pyright: ignore[reportArgumentType]
    try:
        await update.message.delete() # pyright: ignore[reportOptionalMemberAccess]
    except Exception:
        pass
