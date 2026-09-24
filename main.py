import asyncio
import os
import time
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

import config
from engine.market_data import market_manager
from engine.brain import analyst_brain
from engine.vision_analyzer import vision_analyzer
from engine.history import history_manager

app = FastAPI(title="Pocket Trading Signals & AI Vision Terminal", version="2.1.0")

# Enable CORS for Telegram Web App embed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Background tick & market sync task
async def market_tick_loop():
    from AITradingEngine.market_data.pocket_option_adapter import pocket_option_adapter
    sync_counter = 0
    while True:
        try:
            # Tick all pairs to update price and candles
            for p in config.PAIRS["otc"] + config.PAIRS["regular"]:
                tick_info = market_manager.tick_pair(p["id"])
                if tick_info and "price" in tick_info:
                    normalized = pocket_option_adapter.normalize_raw_tick(
                        symbol=p["id"],
                        price=tick_info["price"],
                        source="POCKET_OPTION_LIVE_STREAM"
                    )
                    quant_engine.feed_manager.record_normalized_tick(normalized)

            history_manager.check_active_signals()

            sync_counter += 1
            if sync_counter >= 35: # Sync with real market rates every ~30s
                sync_counter = 0
                await market_manager.sync_with_live_market()

        except Exception as e:
            print(f"Error in tick loop: {e}")
        await asyncio.sleep(0.85)

@app.on_event("startup")
async def startup_event():
    from AITradingEngine.market_data.pocket_option_adapter import pocket_option_adapter
    await pocket_option_adapter.start()
    # Initial live market sync
    try:
        await market_manager.sync_with_live_market()
    except Exception:
        pass
    asyncio.create_task(market_tick_loop())

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
    return market_manager.get_all_pairs()

@app.get("/api/price/{pair_id}")
async def get_single_price(pair_id: str):
    pair_info = market_manager.get_pair_info(pair_id)
    if not pair_info:
        return JSONResponse(status_code=404, content={"error": "Pair not found"})
    cur_p = market_manager.get_current_price(pair_id)
    now = int(time.time())
    sec_rem = 60 - (now % 60)
    return {
        "pair": pair_id,
        "name": pair_info["name"],
        "price": cur_p,
        "precision": pair_info["precision"],
        "payout": pair_info["payout"],
        "category": pair_info["category"],
        "seconds_remaining": sec_rem
    }

@app.get("/api/candles/{pair_id}")
async def get_candles(pair_id: str, timeframe: str = "1m", limit: int = 80):
    candles = market_manager.get_candles(pair_id, timeframe=timeframe, limit=limit)
    pair_info = market_manager.get_pair_info(pair_id)
    cur_p = market_manager.get_current_price(pair_id)
    now = int(time.time())
    sec_rem = 60 - (now % 60)
    return {
        "pair": pair_id,
        "pair_info": pair_info,
        "timeframe": timeframe,
        "candles": candles,
        "current_price": cur_p,
        "seconds_remaining": sec_rem
    }

@app.post("/api/market/calibrate")
async def calibrate_market_price(pair_id: str = Form(...), price: float = Form(...)):
    market_manager.calibrate_price(pair_id, price)
    return {
        "success": True,
        "pair": pair_id,
        "calibrated_price": market_manager.get_current_price(pair_id)
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
    
    # Save to history if valid signal was generated
    if res.get("status") == "SIGNAL_GENERATED":
        record = history_manager.add_signal(res)
        res["signal_id"] = record.signal_id
        res["expires_at"] = record.expires_at
        res["seconds_left"] = record.expiration_minutes * 60
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

@app.get("/api/debugger/price-comparison")
async def get_price_comparison(pair_id: Optional[str] = None):
    return quant_engine.get_price_comparison(pair_id)

@app.get("/api/debugger/health")
async def get_debugger_health():
    from AITradingEngine.market_data.pocket_option_adapter import pocket_option_adapter
    return pocket_option_adapter.get_health_report()

@app.get("/api/scanner/overview")
async def get_scanner_overview():
    results = []
    for p in config.PAIRS["otc"] + config.PAIRS["regular"]:
        feed = quant_engine.feed_manager.feeds.get(p["id"])
        price = feed.current_price if feed else p.get("base_price", 1.0)
        health = feed.check_health() if feed else "OFFLINE"
        results.append({
            "id": p["id"],
            "name": p["name"],
            "category": p.get("category", "CURRENCY"),
            "payout": p.get("payout", 85),
            "price": price,
            "precision": p.get("precision", 5),
            "status": health,
            "market_type": "OTC" if "OTC" in p["id"] else "REAL",
            "cold_start_samples": feed.sample_count if feed else 0
        })
    return results

@app.get("/api/history")
async def get_history():
    return history_manager.get_stats()

@app.get("/api/indicators/{pair_id}")
async def get_indicators(pair_id: str, timeframe: str = "1m"):
    analysis = analyst_brain.analyze_pair(pair_id, timeframe=timeframe)
    if "error" in analysis:
        return JSONResponse(status_code=400, content=analysis)
    return {
        "pair": pair_id,
        "indicators": analysis["indicators"],
        "metrics": analysis["metrics"]
    }

# Live WebSocket for real-time ticks
@app.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    await websocket.accept()
    active_pair = "AUD_CHF_OTC"
    try:
        while True:
            # Check for client messages (e.g. changing pair)
            try:
                msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.85)
                if "pair" in msg and msg["pair"]:
                    active_pair = msg["pair"]
            except asyncio.TimeoutError:
                pass

            cur_p = market_manager.get_current_price(active_pair)
            pair_info = market_manager.get_pair_info(active_pair)
            candles = market_manager.get_candles(active_pair, timeframe="1m", limit=3)
            latest_candle = candles[-1] if candles else None
            now = int(time.time())
            sec_rem = 60 - (now % 60)

            await websocket.send_json({
                "pair": active_pair,
                "price": cur_p,
                "precision": pair_info["precision"] if pair_info else 5,
                "latest_candle": latest_candle,
                "seconds_remaining": sec_rem,
                "timestamp": now
            })
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")

# Quant Engine API Endpoints
from bot import quant_engine
from AITradingEngine.core.enums import Direction

@app.get("/api/quant/status")
async def get_quant_status():
    return quant_engine.get_status_overview()

@app.post("/api/quant/scan")
async def run_quant_scan():
    await quant_engine.scanner.scan_once()
    best = quant_engine.scanner.opportunity_queue.get_top_candidate()
    if not best:
        return {
            "status": "NO_TRADE",
            "message": "All markets currently fail 12-Gate Filter criteria. Preserving capital."
        }
    snapshot, score = best
    signal = await quant_engine.process_candidate_setup(snapshot, score)
    if signal and signal.gate_result.is_passed and signal.direction != Direction.NO_SIGNAL:
        return {
            "status": "SIGNAL_GENERATED",
            "signal": {
                "id": signal.signal_id,
                "symbol": signal.symbol,
                "market_type": signal.market_type.value,
                "direction": signal.direction.value,
                "expiration": signal.expiration_label,
                "confidence": signal.confidence,
                "grade": signal.grade.value,
                "setup": signal.setup_name,
                "confluence": signal.confluence_tags,
                "entry_price": signal.entry_price
            }
        }
    return {
        "status": "NO_TRADE",
        "reason": signal.rejection_reason if signal else "Failed adversarial critique or edge threshold"
    }

@app.get("/api/quant/rejections")
async def get_quant_rejections(limit: int = 20):
    return quant_engine.repository.get_recent_rejections(limit=limit)

@app.get("/api/quant/perf")
async def get_quant_perf():
    return {
        "otc": quant_engine.otc_store.get_metrics(),
        "real": quant_engine.real_store.get_metrics()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)

