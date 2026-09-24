import sys
import os

# Ensure safe console encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import asyncio
import threading
import uvicorn
import config
from main import app
from bot import start_bot


def run_web():
    print(f"[WEB] Starting Web Terminal at http://localhost:{config.PORT} ...")
    uvicorn.run(app, host=config.HOST, port=config.PORT, log_level="info")


def main():
    if config.BOT_TOKEN:
        web_thread = threading.Thread(target=run_web, daemon=True)
        web_thread.start()
        print("[SYSTEM] Web Terminal running in background thread. Starting Telegram bot...")
        asyncio.run(start_bot())
    else:
        print("=" * 60)
        print("[WARNING] BOT_TOKEN is not set in config.py.")
        print(f"[WEB] Web terminal available at http://localhost:{config.PORT}")
        print("=" * 60)
        run_web()


if __name__ == "__main__":
    main()
