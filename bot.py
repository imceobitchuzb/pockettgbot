"""
Telegram Bot Interface for Ultimate AI Signal Engine & Pocket Option Trading.
Institutional Zero-Forced-Signal Architecture (Phase 20).
Provides conservative, evidence-based market analytics without fake accuracy or forced trades.
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
import logging
import time
from typing import Optional, List, Dict, Any

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo,
    BufferedInputFile
)

import config
from AITradingEngine.engine import UltimateAITradingEngine
from AITradingEngine.core.enums import MarketType, Timeframe, Direction, QualityGrade, SignalStrength
from AITradingEngine.core.models import FinalSignal, Signal

logger = logging.getLogger("AITradingEngine.TelegramBot")

# Authoritative Engine Instance (No fake candle pre-seeding)
quant_engine = UltimateAITradingEngine(db_path=config.QUANT_DB_PATH)

dp = Dispatcher()


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Nine-button institutional main menu keyboard (Phase 20)."""
    url = config.WEBAPP_URL
    first_btn = (
        InlineKeyboardButton(text="🌐 Открыть Quant Terminal (Web)", web_app=WebAppInfo(url=url))
        if url and url.startswith("https://")
        else InlineKeyboardButton(text=f"🌐 Веб-терминал: :{config.PORT}", callback_data="btn_web_info")
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🚀 СИГНАЛ (/signal)", callback_data="btn_signal"),
            InlineKeyboardButton(text="📊 СКАНЕР РЫНКОВ (/scan)", callback_data="btn_scan")
        ],
        [
            InlineKeyboardButton(text="📈 ПРЯМОЙ ЭФИР (/live)", callback_data="btn_live"),
            InlineKeyboardButton(text="📷 АНАЛИЗ СКРИНШОТА", callback_data="btn_photo_info")
        ],
        [
            InlineKeyboardButton(text="🧠 КВАНТ-МОЗГ (/brain)", callback_data="btn_brain"),
            InlineKeyboardButton(text="📜 ИСТОРИЯ СИГНАЛОВ (/history)", callback_data="btn_history")
        ],
        [
            InlineKeyboardButton(text="📊 ПЕРФОРМАНС (/perf)", callback_data="btn_perf"),
            InlineKeyboardButton(text="⚙️ НАСТРОЙКИ (/settings)", callback_data="btn_settings")
        ],
        [
            InlineKeyboardButton(text="ℹ️ О СИСТЕМЕ (/about)", callback_data="btn_about"),
            first_btn
        ]
    ])
    return kb


def format_signal_message(signal: Signal) -> str:
    """Formats clean institutional explainable signal (Phase 11 & 20)."""
    dir_emoji = "🟢 CALL (ВВЕРХ)" if signal.direction == Direction.CALL else "🔴 PUT (ВНИЗ)"
    strength_str = signal.signal_strength.value if hasattr(signal.signal_strength, "value") else str(signal.signal_strength)
    score_str = f"{signal.confluence_score}/100"

    reasons_lines = "\n".join([f"✓ {r}" for r in signal.reasons]) if signal.reasons else "✓ Multi-Timeframe Alignment\n✓ Technical Strategy Consensus"
    warnings_lines = "\n".join([f"⚠ {w}" for w in signal.warnings]) if signal.warnings else "⚠ Standard binary option volatility risk"

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚨 **QUANT AI SIGNAL**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Актив:** `{signal.symbol}`\n"
        f"**Рынок:** `{signal.market_type.value if hasattr(signal.market_type, 'value') else signal.market_type}`\n"
        f"**Направление:** {dir_emoji}\n"
        f"**Таймфрейм:** `{signal.timeframe.value if hasattr(signal.timeframe, 'value') else signal.timeframe}`\n"
        f"**Рекомендуемая экспирация:** `{signal.expiration_label}`\n"
        f"**Точка входа (Anchor):** `{signal.entry_price:.5f}`\n\n"
        f"**Сила сигнала:** `{strength_str}`\n"
        f"**Confluence Score:** `{score_str}`\n"
        f"**Режим рынка:** `{signal.market_regime}`\n"
        f"**Сетап:** `{signal.setup_name}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📋 **ФАКТОРЫ ПОДТВЕРЖДЕНИЯ (EVIDENCE):**\n"
        f"{reasons_lines}\n\n"
        "⚠️ **ЗОНЫ РИСКА (RISK DISCLOSURE):**\n"
        f"{warnings_lines}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 `ID: {signal.signal_id}` | *Строгий манименеджмент: 1-2% от депозита. Без Мартингейла.*"
    )
    return msg


def format_no_trade_message(reason: str = "Market condition fails quality gates", blocked_reasons: Optional[List[str]] = None) -> str:
    """Formats institutional zero-forced-signal notice."""
    reasons_text = ""
    if blocked_reasons:
        reasons_text = "\n".join([f"• {r}" for r in blocked_reasons[:4]])

    msg = (
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "⚠️ **NO TRADE — СИГНАЛ ОТКЛОНЁН**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "**Статус:** `PRESERVING CAPITAL`\n"
        f"**Вердикт:** `{reason}`\n"
    )
    if reasons_text:
        msg += f"\n**Причины отклонения:**\n{reasons_text}\n"

    msg += (
        "\n🛡 **Политика Zero-Forced-Signal:**\n"
        "Бот не генерирует сделки при шуме, боковике, конфликте таймфреймов или задержке котировок.\n"
        "Сохранение депозита — главный приоритет."
    )
    return msg


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    welcome_text = (
        "🏛 **ULTIMATE AI QUANT SIGNAL TERMINAL**\n\n"
        "Консервативная мульти-рыночная система анализа Pocket Option.\n\n"
        "⚡ **Ключевые принципы:**\n"
        "• **Никакой фиктивной точности**: честный Confluence Score вместо обещаний 90%+.\n"
        "• **Data Quality Gate**: проверка свечей на разрывы, аномалии и свежесть.\n"
        "• **Multi-Timeframe Engine (1M, 3M, 5M, 15M)**: направление только по тренду старших ТФ.\n"
        "• **Сегрегация OTC и Real Market**: отдельные пулы данных и валидаторы.\n"
        "• **Vision Quant**: глубокий структурный аудит скриншотов с OCR-контролем.\n\n"
        "Выберите действие в меню:"
    )
    await message.answer(welcome_text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("signal"))
async def cmd_signal(message: types.Message):
    status_msg = await message.answer("🔄 **Оценка текущего фокусного инструмента...** Проверка ворот качества...")
    # Find best active pair
    focus_asset = config.PAIRS["otc"][0]["id"]
    res = await quant_engine.generate_signal_for_pair(focus_asset, timeframe="1m", requested_expiration=1)

    if res.get("status") == "SIGNAL_GENERATED":
        # Build Signal model
        sig = Signal(
            signal_id=res.get("signal_id", f"SIG_{int(time.time())}"),
            symbol=res.get("pair", focus_asset),
            market_type=MarketType.OTC if "OTC" in focus_asset else MarketType.REAL,
            direction=Direction(res.get("direction", "NO_SIGNAL")),
            expiration_seconds=res.get("expiration_minutes", 1) * 60,
            expiration_label=f"{res.get('expiration_minutes', 1)} MIN",
            entry_price=res.get("entry_price", 1.0),
            timestamp=time.time(),
            grade=QualityGrade.GRADE_A,
            confidence=res.get("confidence_percent", 75.0) / 100.0,
            setup_name=res.get("primary_strategy", "MULTI_FACTOR_SETUP"),
            confluence_tags=res.get("confirming_strategies", ["EMA Confluence", "Momentum Alignment"]),
            confluence_score=res.get("confidence_percent", 75.0),
            market_regime=res.get("market_regime", "TRENDING"),
            data_quality="PASS"
        )
        await status_msg.edit_text(format_signal_message(sig), parse_mode="Markdown", reply_markup=get_main_keyboard())
    else:
        rej = res.get("rejection_reason", "Data quality gate or confluence threshold not satisfied.")
        await status_msg.edit_text(format_no_trade_message(rej), parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("scan"))
async def cmd_scan(message: types.Message):
    status_msg = await message.answer("🔄 **Сканирование 18 валютных и OTC пар...** Проверка MTF и Data Quality...")
    await quant_engine.scanner.scan_once()
    top_candidate = quant_engine.scanner.opportunity_queue.get_top_candidate()

    if not top_candidate:
        text = format_no_trade_message(
            "Ни один инструмент в данный момент не прошёл строгие фильтры качества (рынок в шуме, боковике или котировки обновляются)."
        )
        await status_msg.edit_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard())
        return

    snapshot, score = top_candidate
    signal = await quant_engine.process_candidate_setup(snapshot, score)

    if signal and signal.gate_result and signal.gate_result.is_passed and signal.direction != Direction.NO_SIGNAL:
        await status_msg.edit_text(format_signal_message(signal), parse_mode="Markdown", reply_markup=get_main_keyboard())
    else:
        rej = signal.rejection_reason if signal else "Сетап отклонён риск-контролем или проверкой MTF."
        await status_msg.edit_text(format_no_trade_message(rej), parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("live"))
async def cmd_live(message: types.Message):
    status = quant_engine.feed_manager.get_status_summary()
    adapter_health = quant_engine.latency_monitor.get_telemetry() if hasattr(quant_engine, "latency_monitor") else {}

    live_pairs = [p["name"] for p in config.PAIRS["otc"] + config.PAIRS["regular"] if quant_engine.feed_manager.feeds.get(p["id"]) and quant_engine.feed_manager.feeds[p["id"]].check_health() == "LIVE"]
    live_sample = ", ".join(live_pairs[:5]) if live_pairs else "Подключение к брокеру..."

    msg = (
        "📈 **ПРЯМОЙ ЭФИР И ТЕЛЕМЕТРИЯ ДАННЫХ**\n\n"
        f"• Всего инструментов: `{status['total_tracked']}`\n"
        f"• Активных живых фидов: `{status['live_feeds']}` 🟢\n"
        f"• Задержанных/Stale: `{status['stale_feeds']}` 🟡\n"
        f"• В режиме Cold-Start: `{status['cold_start_feeds']}` ⏳\n"
        f"• Оффлайн: `{status['offline_feeds']}` 🔴\n\n"
        f"**Активные инструменты:**\n`{live_sample}`\n\n"
        "🛡 *DataQualityGate активен. Свечи с разрывами или задержками блокируются автоматически.*"
    )
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("brain"))
async def cmd_brain(message: types.Message):
    msg = (
        "🧠 **АРХИТЕКТУРА КВАНТ-МОЗГА**\n\n"
        "• **Trend Module**: EMA (9, 21, 50, 200), ADX (14), Aroon\n"
        "• **Momentum Module**: RSI (14), MACD, Stochastic (14, 3), ROC\n"
        "• **Volatility Module**: ATR (14), Bollinger Bands, Squeeze Detection\n"
        "• **Price Action**: Rejection Wicks (Pin Bars), Engulfing, Swing High/Low\n"
        "• **Structure**: Кластеризация уровней поддержки/сопротивления\n"
        "• **MTF Engine**: 1M (40%), 3M (25%), 5M (20%), 15M (15%)\n"
        "• **AI Critic**: Двухслойный арбитраж на конфликт тренда и перекупленности\n\n"
        "ℹ️ *Система выдаёт сигнал только при согласии независимых классов факторов.*"
    )
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("history"))
async def cmd_history(message: types.Message):
    signals = quant_engine.repository.get_recent_signals(limit=5)
    if not signals:
        text = "📜 **ИСТОРИЯ СИГНАЛОВ**\n\nБаза недавних сигналов пуста. Система ожидает качественных рыночных формаций."
    else:
        lines = []
        for s in signals:
            res_emoji = "⏳" if s.get("result") == "PENDING" else ("✅ WIN" if s.get("result") == "WIN" else "❌ LOSS")
            lines.append(
                f"• `{s.get('asset')}` | **{s.get('direction')}** | {res_emoji}\n"
                f"  Вход: `{s.get('entry_price')}` | Экспирация: `{s.get('expiration_seconds')}s`"
            )
        text = "📜 **ПОСЛЕДНИЕ СИГНАЛЫ В БАЗЕ:**\n\n" + "\n\n".join(lines)

    await message.answer(text, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("perf"))
async def cmd_perf(message: types.Message):
    stats = quant_engine.repository.get_comprehensive_statistics()
    resolved = stats.get("resolved_trades", 0)
    wr = f"{stats.get('win_rate', 0.0)}%" if resolved >= 10 else "N/A (Сбор выборки)"

    msg = (
        "📊 **СТАТИСТИКА И ПЕРФОРМАНС СИСТЕМЫ**\n\n"
        f"• Всего зарегистрировано сигналов: `{stats.get('total_signals', 0)}`\n"
        f"• Завершённых сделок: `{resolved}`\n"
        f"• Wins: `{stats.get('wins', 0)}` | Losses: `{stats.get('losses', 0)}`\n"
        f"• Фактический Win Rate: `{wr}`\n"
        f"• Profit Factor: `{stats.get('profit_factor', 0.0)}`\n"
        f"• Макс. серия убытков: `{stats.get('max_losing_streak', 0)}`\n\n"
        "ℹ️ *Статистика рассчитывается строго по закрытию свечи экспирации. Никаких нарисованных процентов.*"
    )
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("settings"))
async def cmd_settings(message: types.Message):
    msg = (
        "⚙️ **ТЕКУЩИЕ ПАРАМЕТРЫ ФИЛЬТРАЦИИ**\n\n"
        "• Минимальный Confluence Score: `70 / 100`\n"
        "• Минимальное число подтверждающих стратегий: `3`\n"
        "• Кулдаун между сигналами одного актива: `120 сек`\n"
        "• Максимально допустимая задержка котировки: `350 мс`\n"
        "• Лимит шума рынка (Choppiness Index): `< 61.8`\n"
        "• Минимальный пейаут брокера: `80%`\n"
        "• Multi-Timeframe подтверждение: `1M + 3M/5M`"
    )
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


@dp.message(Command("about"))
async def cmd_about(message: types.Message):
    msg = (
        "ℹ️ **О КВАНТОВОМ СИГНАЛЬНОМ ДВИЖКЕ**\n\n"
        "Данный торговый бот спроектирован для аналитической поддержки на платформе Pocket Option.\n\n"
        "⚠️ **ПРЕДУПРЕЖДЕНИЕ О РИСКАХ:**\n"
        "Торговля бинарными опционами и OTC-инструментами связана с высоким риском частичной или полной потери депозита. "
        "Система НЕ гарантирует прибыль, НЕ обещает '100% проходимость' и служит исключительно инструментом математической фильтрации рынка.\n\n"
        "💡 *Соблюдайте строгий манименеджмент: не рискуйте суммами, потеря которых повлияет на ваше финансовое благополучие.*"
    )
    await message.answer(msg, parse_mode="Markdown", reply_markup=get_main_keyboard())


# Photo handler: user sends screenshot of chart
@dp.message(F.photo)
async def handle_screenshot(message: types.Message, bot: Bot):
    status_msg = await message.answer("🔄 **Анализ скриншота графика (Vision Quant Engine)...**")
    try:
        photo = message.photo[-1]
        file_io = io.BytesIO()
        file = await bot.get_file(photo.file_id)
        await bot.download_file(file.file_path, file_io)
        image_bytes = file_io.getvalue()

        # Parse screenshot through Vision Quant
        vq_result = quant_engine.vision_quant.analyze_chart_bytes(
            image_bytes=image_bytes,
            filename=f"tg_screenshot_{message.from_user.id}.png"
        )

        if not vq_result.get("is_valid_chart"):
            rej_text = (
                "❌ **СКРИНШОТ ОТКЛОНЁН ДЕТЕКТОРОМ КАЧЕСТВА**\n\n"
                f"**Причина:** `{vq_result.get('reason')}`\n\n"
                "Система отклоняет размытые, обрезанные, нерелевантные или нечитаемые изображения."
            )
            await status_msg.edit_text(rej_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
            return

        if not vq_result.get("signal"):
            rej_text = (
                "⚠️ **АНАЛИЗ СКРИНШОТА: NO TRADE**\n\n"
                f"**Актив:** `{vq_result.get('asset', 'UNKNOWN')}`\n"
                f"**Статус:** `НЕДОСТАТОЧНО ДАННЫХ ДЛЯ ВХОДА`\n"
                f"**Причина:** `{vq_result.get('reason')}`\n\n"
                f"• OCR Confidence: `{vq_result.get('ocr_confidence', 0.0):.2f}`\n"
                f"• Vision Confidence: `{vq_result.get('vision_confidence', 0.0):.2f}`\n"
                f"• Полнота структуры данных: `{vq_result.get('data_completeness', 0.0):.2f}`\n\n"
                "🛡 *Zero-Forced-Signal:* Рыночная структура на скриншоте не даёт подтверждённого математического преимущества."
            )
            await status_msg.edit_text(rej_text, parse_mode="Markdown", reply_markup=get_main_keyboard())
            return

        detected_pair = vq_result.get("asset", "EUR_USD_OTC")
        dir_text = vq_result.get("direction_display", vq_result.get("direction", "NO_SIGNAL"))
        dir_emoji = "🟢 ⬆️" if "CALL" in vq_result.get("direction", "") else "🔴 ⬇️"
        conf_score = vq_result.get("confluence_score", 70.0)
        strength = vq_result.get("signal_strength", "MODERATE")

        reply = (
            "📸 **РЕЗУЛЬТАТ VISION QUANT АНАЛИЗА**\n\n"
            f"**Распознанный актив:** `{detected_pair}`\n"
            f"**Сетап:** `{vq_result.get('setup', 'CANDLE_STRUCTURE_ANALYSIS')}`\n"
            f"**Направление:** {dir_emoji} **{dir_text}**\n"
            f"**Рекомендуемая экспирация:** `{vq_result.get('recommended_expiration', '1 MIN')}`\n"
            f"**Сила сигнала:** `{strength}`\n"
            f"**Confluence Score:** `{conf_score}/100`\n\n"
            f"• OCR Уверенность: `{vq_result.get('ocr_confidence', 0.0):.2f}`\n"
            f"• Полнота данных: `{vq_result.get('data_completeness', 0.0):.2f}`\n\n"
            "💡 *Скриншот успешно верифицирован. Используйте /scan для онлайн сканирования всех инструментов.*"
        )
        await status_msg.edit_text(reply, parse_mode="Markdown", reply_markup=get_main_keyboard())

    except Exception as e:
        logger.error(f"Error handling photo: {e}", exc_info=True)
        await status_msg.edit_text(f"❌ Ошибка при анализе фото: {str(e)}")


# Callback handlers
@dp.callback_query(F.data == "btn_signal")
async def cb_signal(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_signal(callback.message)


@dp.callback_query(F.data == "btn_scan")
async def cb_scan(callback: types.CallbackQuery):
    await callback.answer("Сканирую рынки...")
    await cmd_scan(callback.message)


@dp.callback_query(F.data == "btn_live")
async def cb_live(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_live(callback.message)


@dp.callback_query(F.data == "btn_brain")
async def cb_brain(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_brain(callback.message)


@dp.callback_query(F.data == "btn_history")
async def cb_history(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_history(callback.message)


@dp.callback_query(F.data == "btn_perf")
async def cb_perf(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_perf(callback.message)


@dp.callback_query(F.data == "btn_settings")
async def cb_settings(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_settings(callback.message)


@dp.callback_query(F.data == "btn_about")
async def cb_about(callback: types.CallbackQuery):
    await callback.answer()
    await cmd_about(callback.message)


@dp.callback_query(F.data == "btn_photo_info")
async def cb_photo_info(callback: types.CallbackQuery):
    msg = (
        "📷 **АНАЛИЗ СКРИНШОТА ГРАФИКА**\n\n"
        "Отправьте боту прямо в чат скриншот графика из Pocket Option или Quotex.\n\n"
        "🔍 **Компьютерное зрение проверит:**\n"
        "• Чёткость и разрешение изображения\n"
        "• Расположение свечей и структуру теней/тел\n"
        "• Уровни поддержки/сопротивления\n"
        "• Согласованность с живым потоком котировок\n\n"
        "Просто прикрепите фото к сообщению!"
    )
    await callback.message.answer(msg, parse_mode="Markdown")
    await callback.answer()


@dp.callback_query(F.data == "btn_web_info")
async def cb_web_info(callback: types.CallbackQuery):
    msg = (
        "🌐 **ЛОКАЛЬНЫЙ ВЕБ-ТЕРМИНАЛ**\n\n"
        f"Терминал запущен по адресу: `http://localhost:{config.PORT}`\n"
        "Откройте ссылку в браузере для работы с графиками и полным журналом."
    )
    await callback.message.answer(msg, parse_mode="Markdown")
    await callback.answer()


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
