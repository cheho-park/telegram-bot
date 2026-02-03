"""Attendance-related handlers."""
from telegram import Update
from telegram.ext import ContextTypes

from .. import utils
from ..services import attendance_service
from ..utils import extract_ttl_from_args
from .telegram_utils import send_temporary_message


async def attend(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args)
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    res = await attendance_service.attend(user.id)
    if res.status == "error":
        await send_temporary_message(update, context, res.error_message or "출석 처리 중 오류가 발생했습니다.", ttl=ttl)
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    if res.status == "already":
        await update.message.reply_text("이미 오늘 출석하셨습니다. :)")
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    if res.should_notify:
        if res.level_up:
            await send_temporary_message(
                update,
                context,
                f"출석 완료! 축하합니다 — 레벨업! {res.old_level} -> {res.new_level}",
                ttl=8,
            )
        else:
            await send_temporary_message(update, context, "출석 완료! 좋은 하루 되세요.", ttl=6)

    await update.message.reply_text("출석 완료! 좋은 하루 되세요.")
    try:
        await update.message.delete()
    except Exception:
        pass


async def attendance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args)
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

    res = await attendance_service.get_attendance_history(user.id, limit=limit)
    if res.status == "error":
        await update.message.reply_text(res.error_message or "출석 기록 조회 중 오류가 발생했습니다.")
        return
    if res.status == "empty":
        await update.message.reply_text("출석 기록이 없습니다.")
        return

    lines = [f"- {utils.format_ts_kst(ts)}" for ts in (res.timestamps or [])]
    text = "최근 출석 기록:\n" + "\n".join(lines)
    await send_temporary_message(update, context, text, ttl=ttl)
    try:
        await update.message.delete()
    except Exception:
        pass


async def streak(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args)
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    res = await attendance_service.get_streak(user.id)
    if res.status == "error":
        await update.message.reply_text(res.error_message or "연속 출석 조회 중 오류가 발생했습니다.")
        return

    await send_temporary_message(update, context, f"🔥 현재 연속 출석: {res.streak}일", ttl=ttl)
    try:
        await update.message.delete()
    except Exception:
        pass
