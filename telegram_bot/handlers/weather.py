"""Modular weather handlers using weather_service and keyboard helpers."""
from __future__ import annotations
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from typing import List, Tuple
import logging

from ..services import weather_service
from ..utils import format_ts_kst, KST
import datetime

DEFAULT_CITIES: List[Tuple[str, str]] = [
    ("서울", "Seoul"),
    ("부산", "Busan"),
    ("대구", "Daegu"),
    ("광주", "Gwangju"),
    ("인천", "Incheon"),
]


def generate_keyboard(cities, delete_mode: bool = False):
    keyboard = []
    for i in range(0, len(cities), 2):
        row = []
        for name, api in cities[i:i+2]:
            if delete_mode:
                row.append(InlineKeyboardButton(f"🗑️ {name}", callback_data=f"DEL_{api}"))
            else:
                row.append(InlineKeyboardButton(f"📍 {name}", callback_data=api))
        keyboard.append(row)

    if delete_mode:
        keyboard.append([InlineKeyboardButton("⬅️ 뒤로가기", callback_data="Back")])
    else:
        keyboard.append([
            InlineKeyboardButton("➕ 새 지역 추가", callback_data="Add"),
            InlineKeyboardButton("🗑️ 삭제 모드", callback_data="DeleteMode"),
            InlineKeyboardButton("⬅️ 닫기", callback_data="Cancel"),
        ])
    return InlineKeyboardMarkup(keyboard)


async def weather_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "favorites" not in context.user_data:
        context.user_data["favorites"] = DEFAULT_CITIES.copy()
    context.user_data["waiting_for_location"] = False
    await update.message.reply_text(
        "🌦️ <b>실시간 날씨 확인</b>\n\n자주 찾는 도시를 선택하거나 ➕ 버튼으로 새로운 도시를 추가하세요.",
        reply_markup=generate_keyboard(context.user_data["favorites"]),
        parse_mode="HTML",
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    favorites = context.user_data.get("favorites", DEFAULT_CITIES)

    if data == "Add":
        await query.edit_message_text(
            "➕ <b>새로운 지역명을 입력하세요</b>\n예시: <code>서울</code>, <code>부산</code>",
            parse_mode="HTML",
        )
        context.user_data["waiting_for_location"] = True
        return

    if data == "DeleteMode":
        await query.edit_message_text(
            "🗑️ <b>삭제할 도시를 선택하세요</b>",
            reply_markup=generate_keyboard(favorites, delete_mode=True),
            parse_mode="HTML",
        )
        return

    if data == "Back":
        await query.edit_message_text(
            "🌦️ <b>실시간 날씨 확인</b>\n도시를 선택하거나 ➕ 버튼으로 새로운 도시를 추가하세요.",
            reply_markup=generate_keyboard(favorites),
            parse_mode="HTML",
        )
        return

    if data.startswith("DEL_"):
        city_api_name = data.replace("DEL_", "")
        new_favorites = [(n, a) for n, a in favorites if a != city_api_name]
        context.user_data["favorites"] = new_favorites
        await query.edit_message_text(
            "✅ 선택한 도시가 즐겨찾기에서 삭제되었습니다.",
            reply_markup=generate_keyboard(new_favorites),
            parse_mode="HTML",
        )
        return

    if data == "Cancel":
        await query.edit_message_text("✅ 메뉴가 닫혔습니다.")
        context.user_data["waiting_for_location"] = False
        return

    # weather query
    city_api_name = next((api for name, api in favorites if api == data), data)
    weather_data = await weather_service.get_weather_raw(city_api_name)
    if not weather_data:
        await query.edit_message_text(f"⚠️ '{city_api_name}' 지역을 찾을 수 없습니다.")
        return

    info = weather_service.parse_weather_data(weather_data)
    if not info:
        await query.edit_message_text("⚠️ 날씨 정보를 파싱할 수 없습니다.")
        return
    desc, temp, humidity, wind_speed = info
    display_name = next((name for name, api in favorites if api == city_api_name), city_api_name)
    # Construct the display message with last_update below
    # The dt field in weather_data is a unix timestamp. We keep human-friendly timestamp.
    # For now, omit dt formatting; keep concise output.
    dt_ts = weather_data.get("dt")
    if dt_ts:
        dt_iso = datetime.datetime.utcfromtimestamp(int(dt_ts)).replace(tzinfo=datetime.timezone.utc).astimezone(KST).isoformat()
        last_update = format_ts_kst(dt_iso)
    else:
        last_update = "-"

    message = (
        f"🌍 <b>{display_name}</b> 현재 날씨\n\n"
        f"☁️ 상태: <b>{desc}</b>\n"
        f"🌡️ 기온: <b>{temp}°C</b>\n"
        f"💧 습도: <b>{humidity}%</b>\n"
        f"🌬️ 풍속: <b>{wind_speed} m/s</b>\n\n"
        f"🕒 데이터 시각: <b>{last_update}</b>"
    )
    await query.edit_message_text(text=message, reply_markup=generate_keyboard(favorites), parse_mode="HTML")


async def add_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("waiting_for_location", False):
        return
    user_input = update.message.text.strip()
    if not user_input:
        await update.message.reply_text("⚠️ 올바른 지역명을 입력하세요.")
        return
    city_api_name = (user_input if not isinstance(user_input, str) else user_input)
    if not await weather_service.get_weather_raw(city_api_name):
        await update.message.reply_text("⚠️ 올바른 지역명을 입력하세요. (API에서 인식되지 않음)")
        return
    favorites = context.user_data.setdefault("favorites", DEFAULT_CITIES.copy())
    if any(api == city_api_name for _, api in favorites):
        await update.message.reply_text(f"⚠️ '{user_input}'은 이미 즐겨찾기에 있습니다.")
        context.user_data["waiting_for_location"] = False
        return
    favorites.append((user_input, city_api_name))
    context.user_data["waiting_for_location"] = False
    await update.message.reply_text(
        f"✅ '{user_input}' 지역이 즐겨찾기에 추가되었습니다.", reply_markup=generate_keyboard(favorites)
    )
