"""
Integration Smoke Test Suite for Ultimate AI Trading Engine.
Tests indicators, DataQualityGate, Quant Engine pipeline, and Vision Quant.
"""
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from AITradingEngine.technical_analysis.trend import calc_ema, calc_sma, calc_macd
from AITradingEngine.technical_analysis.momentum import calc_rsi, calc_stochastic
from AITradingEngine.technical_analysis.volatility import calculate_bollinger_bands, calculate_atr
from AITradingEngine.market_data.data_quality_gate import data_quality_gate, QualityVerdict
from AITradingEngine.core.models import Candle
from AITradingEngine.screenshot_analyzer.vision_quant import vision_quant
from AITradingEngine.engine import UltimateAITradingEngine


def test_indicators():
    prices = [100.0 + i * 0.2 + (i % 3) * 0.1 for i in range(50)]
    rsi = calc_rsi(prices, period=14)
    ema9 = calc_ema(prices, 9)
    macd = calc_macd(prices)

    assert 0 <= rsi <= 100
    assert len(ema9) == len(prices)
    assert "hist" in macd


def test_data_quality_gate():
    import time
    now = int(time.time()) - 2400
    candles = []
    p = 1.0850
    for i in range(40):
        candles.append(Candle(
            timestamp=now + (i * 60),
            open=p,
            high=p + 0.0005,
            low=p - 0.0005,
            close=p + 0.0001,
            volume=100.0,
            is_closed=True
        ))
        p += 0.0001

    verdict = data_quality_gate.evaluate(candles)
    assert verdict.verdict in (QualityVerdict.PASS, QualityVerdict.WARN)
    assert verdict.score >= 60.0


def test_quant_engine_initialization():
    engine = UltimateAITradingEngine(db_path="data/test_quant.db")
    overview = engine.get_status_overview()
    assert "system_state" in overview
    assert "active_assets_count" in overview


def test_vision_quant_blank_rejection():
    from PIL import Image
    import io
    img = Image.new("RGB", (300, 300), color="black")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    res = vision_quant.analyze_chart_bytes(buf.getvalue())
    assert res["is_valid_chart"] is False
    assert res["signal"] is False
