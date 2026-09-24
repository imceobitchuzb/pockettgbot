"""
Master FastAPI Server & Webhook/WebSocket Gateway.
Institutional Dark Trading Terminal & Authoritative Signal API (Phase 21, 22, 24).
Routes all Web, API, and WebSocket requests directly through the Ultimate AI Trading Engine.
Zero synthetic noise, zero fake performance claims.
"""
import asyncio
import os
import time
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import config
from AITradingEngine.engine import UltimateAITradingEngine
from AITradingEngine.core.enums import MarketType, Timeframe, Direction, QualityGrade
from AITradingEngine.core.models import FinalSignal, Signal

app = FastAPI(title="Pocket Option Quant Trading Terminal", version="3.0.0")

# Enable CORS for Telegram Web App embed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Authoritative Engine Instance
quant_engine = UltimateAITradingEngine(db_path=config.QUANT_DB_PATH)


# Background engine supervisor & feed health monitor
async def engine_monitor_loop():
    while True:
        try:
            # Check active pending signals against live price for resolution
            active_signals = quant_engine.repository.get_active_signals()
            now = time.time()
            for s in active_signals:
                valid_until = s.get("valid_until", s.get("timestamp", 0) + s.get("expiration_seconds", 60))
                if now >= valid_until:
                    asset = s.get("asset")
                    cur_p = quant_engine.feed_manager.get_current_price(asset)
                    entry_p = s.get("entry_price", cur_p)
                    direction = s.get("direction")
                    payout = s.get("payout", 0.85)

                    if cur_p > 0 and entry_p > 0:
                        if direction == "CALL":
                            is_win = cur_p > entry_p
                        else:
                            is_win = cur_p < entry_p

                        result_str = "WIN" if is_win else "LOSS"
                        pnl = payout if is_win else -1.0
                        quant_engine.repository.update_signal_outcome(
                            signal_id=s["signal_id"],
                            exit_price=cur_p,
                            result=result_str,
                            pnl=pnl
                        )
        except Exception as e:
            print(f"[ENGINE_LOOP_ERROR] {e}")
        await asyncio.sleep(2.0)


@app.on_event("startup")
async def startup_event():
    # Start live broker quote adapter & authentic real market data sync
    from AITradingEngine.market_data.pocket_option_adapter import pocket_option_adapter
    await pocket_option_adapter.start()
    await quant_engine.feed_manager.real_provider.start_live_sync()
    asyncio.create_task(engine_monitor_loop())


# Static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>Терминал загружается...</h1>")


@app.get("/api/pairs")
async def get_pairs():
    otc_list = []
    regular_list = []

    for p in config.PAIRS["otc"]:
        p_copy = p.copy()
        feed = quant_engine.feed_manager.feeds.get(p["id"])
        p_copy["current_price"] = feed.current_price if feed else p.get("base_price", 1.0)
        p_copy["health"] = feed.check_health() if feed else "OFFLINE"
        otc_list.append(p_copy)

    for p in config.PAIRS["regular"]:
        p_copy = p.copy()
        feed = quant_engine.feed_manager.feeds.get(p["id"])
        p_copy["current_price"] = feed.current_price if feed else p.get("base_price", 1.0)
        p_copy["health"] = feed.check_health() if feed else "OFFLINE"
        regular_list.append(p_copy)

    return {"otc": otc_list, "regular": regular_list}


@app.get("/api/price/{pair_id}")
async def get_single_price(pair_id: str):
    all_pairs = config.PAIRS["otc"] + config.PAIRS["regular"]
    pair_info = next((p for p in all_pairs if p["id"] == pair_id), None)
    if not pair_info:
        return JSONResponse(status_code=404, content={"error": "Pair not found"})

    feed = quant_engine.feed_manager.feeds.get(pair_id)
    cur_p = feed.current_price if feed else pair_info.get("base_price", 1.0)
    health = feed.check_health() if feed else "OFFLINE"
    now = int(time.time())
    sec_rem = 60 - (now % 60)

    last_t = feed.last_tick_time if feed else 0.0
    latency_ms = round((time.time() - last_t) * 1000.0, 1) if last_t > 0 else 9999.0

    return {
        "pair": pair_id,
        "name": pair_info["name"],
        "price": cur_p,
        "precision": pair_info["precision"],
        "payout": pair_info["payout"],
        "category": pair_info["category"],
        "market_type": "OTC" if "OTC" in pair_id else "REAL",
        "status": health,
        "latency_ms": latency_ms,
        "seconds_remaining": sec_rem
    }


@app.get("/api/candles/{pair_id}")
async def get_candles(pair_id: str, timeframe: str = "1m", limit: int = 80):
    all_pairs = config.PAIRS["otc"] + config.PAIRS["regular"]
    pair_info = next((p for p in all_pairs if p["id"] == pair_id), None)

    tf_map = {
        "1m": Timeframe.M1,
        "3m": Timeframe.M3,
        "5m": Timeframe.M5,
        "15m": Timeframe.M15
    }
    tf_enum = tf_map.get(timeframe.lower(), Timeframe.M1)

    candles = quant_engine.feed_manager.get_closed_candles(pair_id, tf=tf_enum, limit=limit)
    feed = quant_engine.feed_manager.feeds.get(pair_id)
    cur_p = feed.current_price if feed else 0.0

    now = int(time.time())
    sec_rem = 60 - (now % 60)

    return {
        "pair": pair_id,
        "pair_info": pair_info,
        "timeframe": timeframe,
        "candles": [c.to_dict() for c in candles],
        "current_price": cur_p,
        "seconds_remaining": sec_rem,
        "status": feed.check_health() if feed else "OFFLINE"
    }


@app.post("/api/signal/generate")
async def generate_signal(pair_id: str = Form(...), timeframe: str = Form("1m"), expiration: int = Form(1)):
    # Run through full institutional 12-Gate Filter
    res = await quant_engine.generate_signal_for_pair(
        pair_id=pair_id,
        timeframe=timeframe,
        requested_expiration=expiration
    )
    if "error" in res:
        return JSONResponse(status_code=400, content=res)

    return res


@app.post("/api/signal/analyze-image")
async def analyze_image(
    file: UploadFile = File(...),
    asset_hint: Optional[str] = Form(None),
    timeframe_hint: Optional[str] = Form(None)
):
    contents = await file.read()
    result = quant_engine.vision_quant.analyze_chart_bytes(
        image_bytes=contents,
        filename=file.filename or "screenshot.png",
        asset_hint=asset_hint,
        timeframe_hint=timeframe_hint
    )
    if not result.get("is_valid_chart") or not result.get("signal"):
        return result

    pair_id = result.get("asset", "EUR_USD_OTC")
    cur_p = quant_engine.feed_manager.get_current_price(pair_id)
    if cur_p > 0:
        result["entry_price"] = cur_p
        delta = cur_p * 0.00025
        result["target_exit_price"] = round(cur_p + delta if result["direction"] == "CALL" else cur_p - delta, 5)

    return result


@app.get("/api/settings")
async def get_settings():
    from AITradingEngine.core.signal_config import signal_config_manager
    return signal_config_manager.config.to_dict()


@app.post("/api/settings")
async def update_settings(data: dict):
    from AITradingEngine.core.signal_config import signal_config_manager
    updated = signal_config_manager.update(data, engine=quant_engine)
    return {"success": True, "settings": updated.to_dict()}


@app.post("/api/settings/reset")
async def reset_settings():
    from AITradingEngine.core.signal_config import signal_config_manager
    reset = signal_config_manager.reset_to_defaults(engine=quant_engine)
    return {"success": True, "settings": reset.to_dict()}


@app.get("/api/live-status")
async def get_live_status():
    """Live broker telemetry and data quality status (Phase 22)."""
    summary = quant_engine.feed_manager.get_status_summary()
    pairs_telemetry = []

    for p in config.PAIRS["otc"] + config.PAIRS["regular"]:
        feed = quant_engine.feed_manager.feeds.get(p["id"])
        last_t = feed.last_tick_time if feed else 0.0
        age = round(time.time() - last_t, 2) if last_t > 0 else 9999.0
        candles_count = len(quant_engine.feed_manager.get_closed_candles(p["id"], Timeframe.M1, limit=100))
        pairs_telemetry.append({
            "id": p["id"],
            "name": p["name"],
            "market_type": "OTC" if "OTC" in p["id"] else "REAL",
            "price": feed.current_price if feed else 0.0,
            "status": feed.check_health() if feed else "OFFLINE",
            "age_seconds": age,
            "closed_candles": candles_count,
            "provider": "POCKET_OPTION_OTC" if "OTC" in p["id"] else "INTERBANK_REAL"
        })

    return {
        "summary": summary,
        "pairs": pairs_telemetry
    }


@app.get("/api/history")
async def get_history():
    recent = quant_engine.repository.get_recent_signals(limit=25)
    return {"signals": recent}


@app.get("/api/performance")
async def get_performance():
    stats = quant_engine.repository.get_comprehensive_statistics()
    return stats
