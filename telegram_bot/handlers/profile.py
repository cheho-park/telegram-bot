"""Profile-related handlers: register, me, xp, leaderboard."""
from telegram import Update
from telegram.ext import ContextTypes

from .. import utils
from ..services import user_service, xp_service, leaderboard_service
from ..utils import extract_ttl_from_args
from .telegram_utils import send_temporary_message


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args)
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    res = await user_service.register_user(user.id, user.username)
    if res.status == "error":
        await update.message.reply_text(f"등록 중 오류가 발생했습니다: {res.error_message}")
        return

    if res.status == "exists":
        username_text = utils.format_username(user.username, user.id)
        await send_temporary_message(
            update,
            context,
            f"이미 등록되어 있습니다 — {username_text}",
            ttl=ttl,
        )
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    if res.status == "created":
        username_text = utils.format_username(user.username, user.id)
        await send_temporary_message(
            update,
            context,
            f"등록되었습니다 — 환영합니다 {username_text}! 🎉\n레벨: 1, XP: 0",
            ttl=ttl,
        )
        try:
            await update.message.delete()
        except Exception:
            pass
        return

    await update.message.reply_text(f"등록 결과: {res.raw_result}")


async def me(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args)
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    res = await user_service.get_profile(user.id)
    if res.status == "error":
        await update.message.reply_text(f"조회 중 오류가 발생했습니다: {res.error_message}")
        return
    if res.status == "not_found":
        await update.message.reply_text("등록된 정보가 없습니다.")
        return

    username = utils.format_username(res.username, res.user_id)
    await send_temporary_message(
        update,
        context,
        f"{username}\n"
        f"{utils.format_xp_progress(res.xp, res.level, res.next_xp)}\n"
        f"마지막 활동: {utils.format_ts_kst(res.last_xp_at)}",
        ttl=ttl,
    )
    try:
        await update.message.delete()
    except Exception:
        pass


async def xp(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args)
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    res = await xp_service.get_xp_info(user.id)
    if res.status == "error":
        await update.message.reply_text(f"XP 정보 조회 중 오류가 발생했습니다: {res.error_message}")
        return

    await send_temporary_message(
        update,
        context,
        utils.format_xp_progress(res.xp, res.level, res.next_xp),
        ttl=ttl,
    )
    try:
        await update.message.delete()
    except Exception:
        pass


async def leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ttl = extract_ttl_from_args(context.args)
    limit = 10
    if context.args:
        try:
            limit = int(context.args[0])
        except ValueError:
            pass

    res = await leaderboard_service.get_leaderboard(limit=limit)
    if res.status == "error":
        await update.message.reply_text(res.error_message or "리더보드 조회 중 오류가 발생했습니다.")
        return
    if res.status == "empty":
        await update.message.reply_text("리더보드가 비어 있습니다.")
        return

    await send_temporary_message(
        update,
        context,
        "🏆 리더보드:\n" + utils.format_leaderboard(res.rows or []),
        ttl=ttl,
    )
    try:
        await update.message.delete()
    except Exception:
        pass
