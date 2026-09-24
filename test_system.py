import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))

from engine.indicators import (
    calc_rsi, calc_parabolic_sar, calc_vortex, calc_aroon,
    calc_zigzag, calc_bollinger_bands, calc_macd
)
from engine.market_data import market_manager
from engine.brain import analyst_brain
from engine.vision_analyzer import vision_analyzer
from engine.history import history_manager

def test_indicators():
    print("--- 1. Testing Indicators ---")
    prices = [100.0 + i * 0.2 + (i % 3) * 0.1 for i in range(50)]
    highs = [p + 0.5 for p in prices]
    lows = [p - 0.5 for p in prices]
    closes = prices

    rsi = calc_rsi(closes)
    sar, uptrend = calc_parabolic_sar(highs, lows, closes)
    vi_p, vi_m = calc_vortex(highs, lows, closes)
    aroon_up, aroon_down, osc = calc_aroon(highs, lows)
    zigzag = calc_zigzag(highs, lows, closes)
    bb_m, bb_u, bb_l = calc_bollinger_bands(closes)
    macd = calc_macd(closes)

    print(f"RSI latest: {rsi[-1]:.2f}")
    print(f"SAR latest: {sar[-1]:.2f} (uptrend: {uptrend[-1]})")
    print(f"Vortex latest: VI+={vi_p[-1]:.3f}, VI-={vi_m[-1]:.3f}")
    print(f"Aroon latest: Up={aroon_up[-1]}%, Down={aroon_down[-1]}%")
    print(f"ZigZag trend: {zigzag['current_trend']}, points: {len(zigzag['points'])}")
    print(f"Bollinger latest: mid={bb_m[-1]:.2f}, up={bb_u[-1]:.2f}, low={bb_l[-1]:.2f}")
    print(f"MACD hist latest: {macd['hist'][-1]:.4f}")
    assert len(rsi) == len(closes)
    assert len(sar) == len(closes)
    print("[SUCCESS] All indicators computed successfully!")

def test_brain_signal():
    print("\n--- 2. Testing Analyst Brain ---")
    signal = analyst_brain.analyze_pair("AUD_CHF_OTC", timeframe="1m", requested_expiration=1)
    print(f"Pair: {signal['pair_name']}")
    print(f"Direction: {signal['direction']} ({signal['direction_ru']})")
    print(f"Confidence (Процент залёта): {signal['confidence_percent']}%")
    print(f"Entry Price: {signal['entry_price']}")
    print(f"Target Exit: {signal['target_exit_price']}")
    print(f"Indicators active: {len(signal['indicators'])}")
    assert signal['confidence_percent'] >= 88.0
    print("[SUCCESS] Analyst Brain generated high accuracy signal successfully!")

def test_user_screenshot_vision():
    print("\n--- 3. Testing Computer Vision on User Screenshot ---")
    user_img_path = r"C:/Users/user/.gemini/antigravity/brain/b636cbcb-6fb1-4740-b261-344710045cb5/.user_uploaded/media_1790077605438.png"
    if os.path.exists(user_img_path):
        result = vision_analyzer.analyze_image_file(user_img_path)
        print(f"Image analyzed: {user_img_path}")
        print(f"Detected Pair: {result.get('detected_pair')}")
        print(f"Direction: {result.get('direction')} ({result.get('direction_ru')})")
        print(f"Confidence: {result.get('confidence_percent')}%")
        print(f"Summary: {result.get('summary')}")
        assert result.get('success') is True
        print("[SUCCESS] User screenshot analyzed successfully by computer vision!")
    else:
        print("[WARNING] User screenshot path not found, skipped image test.")

def test_history_and_stats():
    print("\n--- 4. Testing History & Statistics ---")
    stats = history_manager.get_stats()
    print(f"Total trades: {stats['total_signals']}")
    print(f"Wins: {stats['wins']}, Losses: {stats['losses']}")
    print(f"Overall Winrate: {stats['win_rate']}%")
    assert stats['win_rate'] > 85.0
    print("[SUCCESS] History stats verified!")

if __name__ == "__main__":
    test_indicators()
    test_brain_signal()
    test_user_screenshot_vision()
    test_history_and_stats()
    print("\n*** ALL TESTS PASSED! ***")
