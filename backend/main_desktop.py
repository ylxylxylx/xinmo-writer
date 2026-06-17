"""桌面版入口 — PyWebView + Uvicorn"""
import sys
import json
import threading
import webview
import uvicorn
from pathlib import Path

if getattr(sys, 'frozen', False):
    APP_DIR = Path(sys.executable).parent
    _INTERNAL = APP_DIR / "_internal"
else:
    APP_DIR = Path(__file__).parent.parent
    _INTERNAL = APP_DIR

sys.path.insert(0, str(APP_DIR / "backend"))

# 读取打包好的 config.json
config_path = _INTERNAL / "config.json"
if config_path.exists():
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
else:
    config = {}

db_path = config.get("db_path", "data/novels.db")
if not Path(db_path).is_absolute():
    db_path = str(_INTERNAL / db_path)
Path(db_path).parent.mkdir(parents=True, exist_ok=True)

port = config.get("port", 8077)

from main import app

def start_server():
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    webview.create_window(
        "芯墨·写作工坊",
        f"http://127.0.0.1:{port}",
        width=1400, height=900,
        min_size=(1000, 700),
        resizable=True, confirm_close=True, text_select=True,
    )
    webview.start()
