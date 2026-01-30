"""Core handlers that were previously in `telegram_bot/handlers.py`.
"""
from telegram import Update
from telegram.ext import ContextTypes

from .. import db
from .. import utils
from ..services import xp_service
from ..services import attendance_service
import asyncio
from datetime import datetime, timedelta, timezone


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from ..utils import send_temporary_message
    await send_temporary_message(update, context, "안녕하세요! 봇 뼈대입니다. /help로 도움말 확인하세요.", ttl=6)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from ..utils import send_temporary_message
    text = (
        "🏁 /start — 시작\n"
        "❓ /help — 도움말\n"
        "🏓 /ping — 응답 확인\n"
        "📝 /register — 등록\n"
        "👤 /me — 내 정보\n"
        "🌦️ /weather — 실시간 날씨 확인\n"
        "📅 /attend — 출석 체크 (하루 1회)\n"
        "📋 /attendance [n] — 내 출석 기록 조회 (최근 n개)\n"
        "🔥 /streak — 연속 출석일수 조회\n"
        "⭐ /xp — 내 XP 및 레벨 조회\n"
        "🏆 /leaderboard [n] — XP 기준 상위 n명 확인\n"
    )
    await send_temporary_message(update, context, text, ttl=10)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from ..utils import send_temporary_message
    await send_temporary_message(update, context, "pong", ttl=4)


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return
    # If user already exists, reply once and do not attempt to create again
    try:
        existing = await db.get_user(user.id)
    except Exception as e:
        await update.message.reply_text(f"등록 중 오류가 발생했습니다: {e}")
        return

    existing_data = existing.get("data") if isinstance(existing, dict) else getattr(existing, "data", None)
    if existing_data:
        username_text = utils.format_username(user.username, user.id)
        from ..utils import send_temporary_message
        await send_temporary_message(update, context, f"이미 등록되어 있습니다 — {username_text}", ttl=6)
        return

    try:
        res = await db.create_user(user.id, user.username)
    except Exception as e:
        await update.message.reply_text(f"등록 중 오류가 발생했습니다: {e}")
        return

    data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
    if data:
        username_text = utils.format_username(user.username, user.id)
        from ..utils import send_temporary_message
        await send_temporary_message(update, context, f"등록되었습니다 — 환영합니다 {username_text}! 🎉\n레벨: 1, XP: 0", ttl=7)
    else:
        await update.message.reply_text(f"등록 결과: {res}")


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    try:
        res = await db.get_user(user.id)
    except Exception as e:
        await update.message.reply_text(f"조회 중 오류가 발생했습니다: {e}")
        return

    data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
    if data:
        row = data[0] if isinstance(data, (list, tuple)) and data else data
        # helper to safely extract attributes whether row is dict-like or object
        def _get(k, default=None):
            if isinstance(row, dict):
                return row.get(k, default)
            return getattr(row, k, default)
        username = utils.format_username(_get("username"), _get("id"))
        xp = _get("xp", 0)
        level = _get("level", 1)
        next_xp = db.xp_for_level(level + 1)
        last_xp = _get("last_xp_at")
        await update.message.reply_text(
            f"{username}\n{utils.format_xp_progress(xp, level, next_xp)}\n마지막 활동: {utils.format_ts_kst(last_xp)}"
        )
    else:
        await update.message.reply_text("등록된 정보가 없습니다.")


async def _handle_level_up(update: Update, context: ContextTypes.DEFAULT_TYPE, data: dict) -> None:
    """Handle level-up notification when user completes attendance.
    
    Checks if the attendance record contains level-up data and sends
    appropriate message to the user.
    """
    from ..utils import send_temporary_message
    
    old_level = data.get("old_level") if isinstance(data, dict) else None
    new_level = data.get("new_level") if isinstance(data, dict) else None
    
    if old_level and new_level and new_level > old_level:
        await send_temporary_message(update, context, f"출석 완료! 축하합니다 — 레벨업! {old_level} -> {new_level}", ttl=8)
    else:
        await send_temporary_message(update, context, "출석 완료! 좋은 하루 되세요.", ttl=6)


async def attend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    try:
        already = await db.attended_today(user.id)
    except Exception as e:
        from ..utils import send_temporary_message
        await send_temporary_message(update, context, f"출석 확인 중 오류가 발생했습니다: {e}", ttl=6)
        return

    if already:
        await update.message.reply_text("이미 오늘 출석하셨습니다. :)")
        try:
            res = await db.record_attendance(user.id)
        except Exception as e:
            from ..utils import send_temporary_message
            await send_temporary_message(update, context, f"출석 처리 중 오류가 발생했습니다: {e}", ttl=6)
            return

        data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
        if data:
            await _handle_level_up(update, context, data)
        await update.message.reply_text("출석 완료! 좋은 하루 되세요.")


async def attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    limit = 10
    if context.args:
        try:
            limit = int(context.args[0])
        except ValueError:
            pass

    try:
        res = await db.get_attendance(user.id, limit=limit)
    except Exception as e:
        await update.message.reply_text(f"출석 기록 조회 중 오류가 발생했습니다: {e}")
        return

    data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
    if not data:
        await update.message.reply_text("출석 기록이 없습니다.")
        return

    lines = []
    for row in data:
        ts = row.get("ts") if isinstance(row, dict) else getattr(row, "ts", None)
        lines.append(f"- {utils.format_ts_kst(ts)}")

    text = "최근 출석 기록:\n" + "\n".join(lines)
    await update.message.reply_text(text)


async def _calculate_and_award_xp(user_id: int) -> None:
    """Calculate and award XP for a message, respecting cooldown.
    
    Configuration:
    - MESSAGE_XP: 5 XP per message
    - MESSAGE_COOLDOWN_SEC: 60 seconds between XP awards
    """
    MESSAGE_XP = 5
    MESSAGE_COOLDOWN_SEC = 60

    try:
        # Use cached info to avoid a DB call in most cases
        info = await db.get_xp_info(user_id)
    except Exception as e:
        # Log the error for debugging
        print(f"[ERROR] _calculate_and_award_xp: Failed to get xp info for user {user_id}: {type(e).__name__}: {e}")
        return

    last_xp = info.get("last_xp_at")
    if last_xp:
        if isinstance(last_xp, str) and last_xp.endswith("Z"):
            last_xp = last_xp.replace("Z", "+00:00")
        try:
            last_dt = datetime.fromisoformat(last_xp)
            # Convert to KST for comparison
            kst = timezone(timedelta(hours=9))
            last_dt_kst = last_dt.astimezone(kst)
            now_kst = datetime.now(kst)
            if (now_kst - last_dt_kst).total_seconds() < MESSAGE_COOLDOWN_SEC:
                return
        except Exception:
            pass

    # award xp
    try:
        # Queue XP for background flush for messages (fast path)
        await xp_service.queue_xp(user_id, MESSAGE_XP)
    except Exception as e:
        # Log the error for debugging
        print(f"[ERROR] _calculate_and_award_xp: Failed to queue xp for user {user_id}: {type(e).__name__}: {e}")
        pass


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Award XP for non-command text messages, with cooldown
    user = update.effective_user
    if user is None:
        return
    if not update.message or not update.message.text:
        return
    # ignore commands
    if update.message.text.startswith("/"):
        return

    await _calculate_and_award_xp(user.id)


async def streak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    try:
        s = await db.get_streak(user.id)
    except Exception as e:
        await update.message.reply_text(f"연속 출석 조회 중 오류가 발생했습니다: {e}")
        return

    await update.message.reply_text(f"🔥 현재 연속 출석: {s}일")


async def xp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    try:
        info = await db.get_xp_info(user.id)
    except Exception as e:
        await update.message.reply_text(f"XP 정보 조회 중 오류가 발생했습니다: {e}")
        return

    xp_val = info.get("xp", 0)
    level = info.get("level", 1)
    next_xp = info.get("next_xp") or db.xp_for_level(level + 1)
    await update.message.reply_text(utils.format_xp_progress(xp_val, level, next_xp))


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    limit = 10
    if context.args:
        try:
            limit = int(context.args[0])
        except ValueError:
            pass

    try:
        res = await db.get_leaderboard(limit=limit)
    except Exception as e:
        await update.message.reply_text(f"리더보드 조회 중 오류가 발생했습니다: {e}")
        return

    data = res.get("data") if isinstance(res, dict) else getattr(res, "data", None)
    if not data:
        await update.message.reply_text("리더보드가 비어 있습니다.")
        return

    await update.message.reply_text("🏆 리더보드:\n" + utils.format_leaderboard(data))
