import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# Server configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))

# Telegram Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
WEBAPP_URL = os.getenv("WEBAPP_URL", f"http://localhost:{PORT}")

# Quant Engine Configuration
QUANT_DB_PATH = os.getenv("QUANT_DB_PATH", "data/quant_engine.db")
MIN_CONFIDENCE_THRESHOLD = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.72"))
MAX_ALLOWED_PROBABILITY = float(os.getenv("MAX_ALLOWED_PROBABILITY", "0.89"))
MAX_LATENCY_MS = float(os.getenv("MAX_LATENCY_MS", "350.0"))
CHOPPINESS_THRESHOLD = float(os.getenv("CHOPPINESS_THRESHOLD", "61.8"))
MIN_EDGE_EXPECTANCY = float(os.getenv("MIN_EDGE_EXPECTANCY", "0.05"))

# Available Trading Pairs
PAIRS = {
    "otc": [
        {"id": "AUD_CHF_OTC", "name": "AUD/CHF OTC", "payout": 92, "category": "Currencies OTC", "precision": 5, "base_price": 0.66147},
        {"id": "USD_JPY_OTC", "name": "USD/JPY OTC", "payout": 92, "category": "Currencies OTC", "precision": 3, "base_price": 157.642},
        {"id": "EUR_USD_OTC", "name": "EUR/USD OTC", "payout": 92, "category": "Currencies OTC", "precision": 5, "base_price": 1.08450},
        {"id": "GBP_USD_OTC", "name": "GBP/USD OTC", "payout": 90, "category": "Currencies OTC", "precision": 5, "base_price": 1.27310},
        {"id": "USD_CAD_OTC", "name": "USD/CAD OTC", "payout": 91, "category": "Currencies OTC", "precision": 5, "base_price": 1.36820},
        {"id": "EUR_JPY_OTC", "name": "EUR/JPY OTC", "payout": 89, "category": "Currencies OTC", "precision": 3, "base_price": 170.850},
        {"id": "NZD_USD_OTC", "name": "NZD/USD OTC", "payout": 88, "category": "Currencies OTC", "precision": 5, "base_price": 0.61240},
        {"id": "EUR_CHF_OTC", "name": "EUR/CHF OTC", "payout": 89, "category": "Currencies OTC", "precision": 5, "base_price": 0.96350},
        {"id": "GBP_JPY_OTC", "name": "GBP/JPY OTC", "payout": 92, "category": "Currencies OTC", "precision": 3, "base_price": 200.740},
        {"id": "BTC_USD_OTC", "name": "BTC/USD OTC", "payout": 85, "category": "Crypto OTC", "precision": 2, "base_price": 64500.00},
    ],
    "regular": [
        {"id": "EUR_USD", "name": "EUR/USD", "payout": 84, "category": "Currencies", "precision": 5, "base_price": 1.08512},
        {"id": "GBP_USD", "name": "GBP/USD", "payout": 83, "category": "Currencies", "precision": 5, "base_price": 1.27450},
        {"id": "USD_JPY", "name": "USD/JPY", "payout": 82, "category": "Currencies", "precision": 3, "base_price": 157.810},
        {"id": "AUD_USD", "name": "AUD/USD", "payout": 81, "category": "Currencies", "precision": 5, "base_price": 0.66720},
        {"id": "USD_CAD", "name": "USD/CAD", "payout": 80, "category": "Currencies", "precision": 5, "base_price": 1.36710},
        {"id": "BTC_USDT", "name": "BTC/USDT", "payout": 85, "category": "Crypto", "precision": 2, "base_price": 64800.00},
        {"id": "ETH_USDT", "name": "ETH/USDT", "payout": 84, "category": "Crypto", "precision": 2, "base_price": 3480.00},
        {"id": "GOLD", "name": "XAU/USD (Gold)", "payout": 86, "category": "Commodities", "precision": 2, "base_price": 2345.50},
    ]
}

# Supported expiration times (in minutes)
EXPIRATION_TIMES = [1, 2, 3, 5]

# Default indicator settings matching Pocket Option
INDICATOR_CONFIG = {
    "zigzag": {"depth": 12, "deviation": 5, "backstep": 3},
    "fractal": {"period": 4},
    "parabolic_sar": {"step": 0.02, "max_step": 0.2},
    "vortex": {"period": 14},
    "rsi": {"period": 14, "overbought": 70, "oversold": 30},
    "aroon": {"period": 15},
    "bollinger": {"period": 20, "std_dev": 2.0},
    "macd": {"fast": 12, "slow": 26, "signal": 9},
}
