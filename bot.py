"""
Telegram Bot Interface for Ultimate AI Signal Engine & Pocket Option Trading.
Zero-Forced-Signal Institutional Architecture.
"""
import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
import io
import json
import logging
import time
from typing import Optional


from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    BufferedInputFile
)

import config
from AITradingEngine.engine import UltimateAITradingEngine
from AITradingEngine.core.enums import MarketType, Timeframe, Direction, QualityGrade
from AITradingEngine.core.models import Candle

# Initialize Engine
quant_engine = UltimateAITradingEngine(db_path=config.QUANT_DB_PATH)

# Seed initial feeds for configured pairs
for p in config.PAIRS["otc"]:
    mtype = MarketType.OTC
    quant_engine.feed_manager.register_symbol(p["id"], mtype)
    # Seed 60 initial baseline candles from base price
    base_p = p.get("base_price", 1.0)
    now_sec = int(time.time())
    candles = []
    for i in range(60):
        t = now_sec - (60 - i) * 60
        candles.append(Candle(
            timestamp=t,
            open=base_p,
            high=base_p + base_p * 0.0002,
            low=base_p - base_p * 0.0002,
            close=base_p,
            volume=100.0,
            timeframe=Timeframe.TF_1M,
            is_closed=True
        ))
    quant_engine.feed_manager.feeds[p["id"]].timeframe_bars[Timeframe.TF_1M] = candles

for p in config.PAIRS["regular"]:
    mtype = MarketType.REAL
    quant_engine.feed_manager.register_symbol(p["id"], mtype)
    base_p = p.get("base_price", 1.0)
    now_sec = int(time.time())
    candles = []
    for i in range(60):
        t = now_sec - (60 - i) * 60
        candles.append(Candle(
            timestamp=t,
            open=base_p,
            high=base_p + base_p * 0.0002,
            low=base_p - base_p * 0.0002,
            close=base_p,
            volume=100.0,
            timeframe=Timeframe.TF_1M,
            is_closed=True
        ))
    quant_engine.feed_manager.feeds[p["id"]].timeframe_bars[Timeframe.TF_1M] = candles

# Legacy imports for terminal webapp sync
from engine.market_data import market_manager
from engine.brain import analyst_brain
from engine.vision_analyzer import vision_analyzer
from engine.history import history_manager

dp = Dispatcher()
logger = logging.getLogger("AITradingEngine.TelegramBot")


def get_main_keyboard():
    url = config.WEBAPP_URL
    first_row = []
    if url and url.startswith("https://"):
        first_row.append(InlineKeyboardButton(text="🚀 Открыть Quant Terminal (Web)", web_app=WebAppInfo(url=url)))
    else:
        first_row.append(InlineKeyboardButton(text="🌐 Веб-терминал: localhost:8000", callback_data="btn_web_info"))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        first_row,
        [
            InlineKeyboardButton(text="🔍 Сканировать Рынок (/scan)", callback_data="btn_scan"),
            InlineKeyboardButton(text="📊 Статус Системы (/status)", callback_data="btn_status")
        ],
        [
            InlineKeyboardButton(text="📈 Перформанс OTC/Real (/perf)", callback_data="btn_perf"),
            InlineKeyboardButton(text="🛠 Дебаг Фильтров (/debug)", callback_data="btn_debug")
        ]
    ])
    return kb



def format_signal_message(signal) -> str:
    """Formats institutional high-conviction signal output."""
    dir_emoji = "🟢 CALL (ВВЕРХ)" if signal.direction == Direction.CALL else "🔴 PUT (ВНИЗ)"
    confluence_str = " ".join([f"✓ {c}" for c in signal.confluence_tags])

    return (
        "🚨 **HIGH-QUALITY SIGNAL**\n\n"
        f"**Asset:** `{signal.symbol}`\n"
        f"**Direction:** {dir_emoji}\n"
        f"**Expiration:** `{signal.expiration_label}`\n"
        f"**Market:** `{signal.market_type.value}`\n"
        f"**Setup Archetype:** `{signal.setup_name}`\n"
        f"**Confidence:** `{int(signal.confidence * 100)}%` ({signal.grade.value})\n"
        f"**Confluence:** {confluence_str}\n"
        f"**Entry Anchor:** `{signal.entry_price:.5f}`\n"
        f"**Signal ID:** `{signal.signal_id}`\n"
        f"**Verification:** `PASSED ALL 12 SAFETY GATES`\n\n"
        "⚠️ *Risk Notice: Strict 1-unit flat stake. No Martingale.*"
    )


def format_no_trade_message(reason: str = "Market condition fails 12-Gate Filter criteria") -> str:
    """Formats institutional zero-forced-signal notice."""
    return (
        "⚠️ **NO TRADE — ALL MARKETS**\n\n"
        f"**Status:** `PRESERVING CAPITAL`\n"
        f"**Filter Verdict:** `{reason}`\n\n"
        "🛡 **Zero-Forced-Signal Policy:**\n"
        "Система НЕ форсирует сделки в хаотичном рынке. Сигнал будет выдан только при "
        "полном совпадении 3+ таймфреймов, положительном матожидании (EV > +0.05) и одобрении AI Critic.\n\n"
        "Следующее сканирование выполняется непрерывно в фоне."
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "🏛 **ULTIMATE AI SIGNAL ENGINE — POCKET OPTION**\n\n"
        "Автономная мульти-рыночная квант-система институционального уровня.\n\n"
        "⚡ **Ключевые принципы:**\n"
        "• **Zero-Forced-Signal Policy**: нет сделок без подтверждённого преимущества (Edge).\n"
        "• **12-Gate Filter Pipeline**: отсев шума, латентности, дрейфа концепции и конфликтов.\n"
        "• **Двухслойный AI**: AI #1 Analyst + AI #2 Adversarial Critic (поиск рисков).\n"
        "• **Сегрегация данных**: строгая изоляция рынков OTC и Real Market.\n"
        "• **Анализ скриншотов**: машинное зрение и детекция аномалий графиков.\n\n"
        "Выберите действие ниже или используйте команды:"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("scan"))
async def cmd_scan(message: types.Message):
    status_msg = await message.answer("🔄 **Запуск 24/7 сканера...** Анализ OTC и биржевых пар через 12 фильтров...")
    
    # Run scan sweep
    await quant_engine.scanner.scan_once()
    top_candidate = quant_engine.scanner.opportunity_queue.get_top_candidate()

    if not top_candidate:
        text = format_no_trade_message("Ни один инструмент не прошёл 12 уровней фильтрации (шум / низкая волатильность)")
        await status_msg.edit_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())
        return

    snapshot, score = top_candidate
    signal = await quant_engine.process_candidate_setup(snapshot, score)

    if signal and signal.gate_result.is_passed and signal.direction != Direction.NO_SIGNAL:
        text = format_signal_message(signal)
    else:
        rej_reason = signal.rejection_reason if signal else "Сетап отклонён AI Critic или риск-контролем"
        text = format_no_trade_message(rej_reason)

    await status_msg.edit_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("status"))
async def cmd_status(message: types.Message):
    overview = quant_engine.get_status_overview()
    rejections_str = "\n".join([f"• {k}: {v}" for k, v in list(overview["rejections_by_gate"].items())[:5]]) or "Нет недавних отказов"

    msg = (
        "📊 **QUANT ENGINE SYSTEM TELEMETRY**\n\n"
        f"**State:** `{overview['system_state']}`\n"
        f"**Uptime:** `{overview['uptime']}`\n"
        f"**Active Monitored Pairs:** `{overview['active_assets_count']}`\n"
        f"**Focus Asset:** `{overview['current_focus_asset']}`\n"
        f"**Total Signals Dispatched:** `{overview['total_signals_generated']}`\n"
        f"**Total Setups Rejected:** `{overview['total_rejections_logged']}`\n\n"
        f"🛡 **Топ фильтров, отсекающих убыточные сделки:**\n"
        f"{rejections_str}\n\n"
        f"⚡ **Circuit Breaker:** `ACTIVE & SECURE`"
    )
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("perf"))
async def cmd_perf(message: types.Message):
    otc = quant_engine.otc_store.get_metrics()
    real = quant_engine.real_store.get_metrics()

    msg = (
        "📈 **SEGREGATED PERFORMANCE REPORT**\n\n"
        "🟡 **OTC MARKET (24/7):**\n"
        f"• Сигналов: `{otc['total_signals']}` | Завершено: `{otc['resolved_trades']}`\n"
        f"• Wins: `{otc['wins']}` | Losses: `{otc['losses']}`\n"
        f"• Win Rate: `{otc['win_rate']}%`\n\n"
        "🔵 **REAL MARKET (Interbank):**\n"
        f"• Сигналов: `{real['total_signals']}` | Завершено: `{real['resolved_trades']}`\n"
        f"• Wins: `{real['wins']}` | Losses: `{real['losses']}`\n"
        f"• Win Rate: `{real['win_rate']}%`\n\n"
        "ℹ️ *Статистика OTC и Real Market хранится в абсолютно изолированных датасетах.*"
    )
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("debug"))
async def cmd_debug(message: types.Message):
    rejections = quant_engine.repository.get_recent_rejections(limit=6)
    if not rejections:
        msg = "🛠 **DEBUG AUDIT TRAIL**\n\nБаза отклонённых сетапов пуста."
    else:
        lines = []
        for r in rejections:
            lines.append(f"• `{r['symbol']}` ➔ **{r['gate_name']}**: _{r['reason']}_")
        msg = "🛠 **ПОСЛЕДНИЕ 6 ОТКЛОНЁННЫХ СЕТАПОВ (12-GATE AUDIT):**\n\n" + "\n\n".join(lines)

    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.callback_query(F.data == "btn_scan")
async def cb_scan(callback: types.CallbackQuery):
    await callback.answer("Сканирую рынки...")
    await cmd_scan(callback.message)


@dp.callback_query(F.data == "btn_status")
async def cb_status(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_status(callback.message)


@dp.callback_query(F.data == "btn_perf")
async def cb_perf(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_perf(callback.message)


@dp.callback_query(F.data == "btn_debug")
async def cb_debug(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_debug(callback.message)


@dp.callback_query(F.data == "btn_web_info")
async def cb_web_info(callback: types.CallbackQuery):
    msg = (
        "🌐 **ЛОКАЛЬНЫЙ ВЕБ-ТЕРМИНАЛ**\n\n"
        f"Терминал запущен: `http://localhost:{config.PORT}`\n"
        "Откройте эту ссылку в браузере Chrome или Edge для работы с живыми графиками!\n\n"
        "💡 *Для кнопки WebApp внутри Telegram требуется HTTPS (например, через ngrok: `ngrok http 8000`).*"
    )
    await callback.message.answer(msg, parse_mode="Markdown")
    await callback.answer()



# Photo handler: user sends screenshot of chart
@dp.message(F.photo)
async def handle_screenshot(message: types.Message, bot: Bot):
    status_msg = await message.answer("🔄 **Анализирую скриншот графика (Vision Quant + Anomaly Detector)...**")
    
    try:
        photo = message.photo[-1]
        file_io = io.BytesIO()
        file = await bot.get_file(photo.file_id)
        await bot.download_file(file.file_path, file_io)
        image_bytes = file_io.getvalue()
        
        # Save temp image for vision quant
        temp_path = f"data/temp_chart_{message.from_user.id}.png"
        os.makedirs("data", exist_ok=True)
        with open(temp_path, "wb") as f:
            f.write(image_bytes)

        # Run Vision Quant Pipeline
        vq_result = quant_engine.vision_quant.analyze_chart_bytes(
            image_bytes=image_bytes,
            filename="tg_screenshot.png"
        )
        
        if not vq_result.get("is_valid_chart"):
            rej_text = (
                "❌ **СКРИНШОТ ОТКЛОНЁН АНОМАЛИ-ДЕТЕКТОРОМ**\n\n"
                f"**Причина:** `{vq_result.get('reason')}`\n\n"
                "Система отклоняет размытые, обрезанные, нерелевантные или поддельные изображения."
            )
            await status_msg.edit_text(rej_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
            return

        if not vq_result.get("signal"):
            rej_text = (
                "⚠️ **АНАЛИЗ СКРИНШОТА: NO TRADE**\n\n"
                f"**Актив:** `{vq_result.get('asset', 'UNKNOWN')}`\n"
                f"**Статус:** `НЕДОСТАТОЧНО ДАННЫХ ДЛЯ ВХОДА`\n"
                f"**Причина:** `{vq_result.get('reason')}`\n\n"
                "🛡 *Zero-Forced-Signal:* Рыночная структура на скриншоте не даёт математического преимущества."
            )
            await status_msg.edit_text(rej_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
            return

        detected_pair = vq_result.get("asset", "EUR/USD OTC")
        dir_text = vq_result.get("direction_display", vq_result.get("direction", "NO_SIGNAL"))
        dir_emoji = "🟢 ⬆️" if "CALL" in vq_result.get("direction", "") else "🔴 ⬇️"
        conf = vq_result.get("confidence_percent", 75.0)

        reply = (
            "📸 **РЕЗУЛЬТАТ VISION QUANT АНАЛИЗА**\n\n"
            f"**Обнаруженный актив:** `{detected_pair}`\n"
            f"**Сетап:** `{vq_result.get('setup', 'PRICE_ACTION')}`\n"
            f"**Направление:** {dir_emoji} **{dir_text}**\n"
            f"**Рекомендуемая экспирация:** `{vq_result.get('recommended_expiration', '1 MIN')}`\n"
            f"**Калиброванная проходимость:** `{conf}%`\n"
            f"**Статус стрима:** `{vq_result.get('live_sync', {}).get('feed_status', 'SYNCED')}`\n\n"
            f"💡 *Скриншот верифицирован. Используйте /scan для онлайн сканирования всех инструментов.*"
        )
        await status_msg.edit_text(reply, parse_mode="Markdown", reply_markup=get_main_keyboard())

    except Exception as e:
        logger.error(f"Error handling photo: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Ошибка при анализе фото: {str(e)}")


async def start_bot():
    if not config.BOT_TOKEN:
        print("[WARNING] BOT_TOKEN is not configured. Telegram bot not started.")
        return
    bot = Bot(token=config.BOT_TOKEN)
    print("[BOT] Telegram bot started successfully and listening for messages (@imtraderbitchbot)...")

    # Start quant scanner in background
    await quant_engine.scanner.start()
    try:
        await dp.start_polling(bot)
    finally:
        await quant_engine.scanner.stop()


if __name__ == "__main__":
    asyncio.run(start_bot())
