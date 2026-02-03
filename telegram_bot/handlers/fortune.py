"""Fortune (운세) command handler."""
from __future__ import annotations

import random
import datetime
from telegram import Update
from telegram.ext import ContextTypes

from ..utils import KST, send_temporary_message, extract_ttl_from_args


FORTUNES = [
    "작은 친절이 큰 기회를 부릅니다. 한 번 더 배려해 보세요.",
    "오늘은 속도보다 방향이 중요합니다. 한 박자 천천히.",
    "새로운 아이디어가 떠오르면 바로 메모하세요. 금방 사라집니다.",
    "예상치 못한 연락이 좋은 소식을 가져옵니다.",
    "지금 하는 선택이 다음 주의 흐름을 바꿉니다.",
    "짧은 휴식이 집중력을 크게 올려줍니다.",
    "고민하던 일이 가볍게 풀리는 힌트를 찾게 됩니다.",
    "부드러운 말투가 오늘의 분위기를 좌우합니다.",
    "미루던 일을 끝내면 기분이 깔끔해집니다.",
    "가벼운 산책이 생각 정리에 도움 됩니다.",
    "단호함이 필요한 순간이 옵니다. 기준을 정하세요.",
    "과감한 시도에 작은 행운이 따라옵니다.",
    "작게 시작하면 크게 이어집니다. 첫걸음을 떼 보세요.",
    "오늘은 정리운이 좋습니다. 책상과 마음을 정돈하세요.",
    "새로운 조합이 의외의 성과를 만듭니다.",
    "좋은 질문 하나가 문제를 반쯤 해결합니다.",
    "기존 방식 대신 다른 길을 시험해 보세요.",
    "함께하면 일이 수월해집니다. 도움을 요청하세요.",
    "작은 실패는 더 큰 성공의 방향을 알려줍니다.",
    "오늘의 성실함이 내일의 여유가 됩니다.",
]

LUCKY_COLORS = [
    "파란색",
    "초록색",
    "노란색",
    "주황색",
    "빨간색",
    "하늘색",
    "베이지",
    "회색",
    "검정색",
    "흰색",
]


def _build_daily_rng(user_id: int, date: datetime.date) -> random.Random:
    seed = f"{user_id}-{date.isoformat()}"
    return random.Random(seed)


async def fortune(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return a daily fortune for the user.

    Usage:
    - /fortune: daily fortune (deterministic per user per day, KST)
    - /fortune random: fully random fortune
    """
    ttl = extract_ttl_from_args(context.args)
    user = update.effective_user
    if user is None:
        await update.message.reply_text("사용자 정보를 가져올 수 없습니다.")
        return

    args = [a.lower() for a in (context.args or [])]
    is_random = any(a in {"random", "rand", "r"} for a in args)

    now_kst = datetime.datetime.now(KST)
    if is_random:
        rng = random.Random()
    else:
        rng = _build_daily_rng(user.id, now_kst.date())

    fortune_text = rng.choice(FORTUNES)
    lucky_number = rng.randint(1, 99)
    lucky_color = rng.choice(LUCKY_COLORS)

    mode_text = "랜덤 운세" if is_random else "오늘의 운세"
    message = (
        f"🔮 {mode_text}\n"
        f"• {fortune_text}\n"
        f"• 행운의 숫자: {lucky_number}\n"
        f"• 행운의 색: {lucky_color}\n"
        f"(기준일: {now_kst.strftime('%Y-%m-%d')} KST)"
    )

    await send_temporary_message(update, context, message, ttl=ttl)
    try:
        await update.message.delete()
    except Exception:
        pass
