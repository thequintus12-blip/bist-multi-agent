"""
Basit JSON dosyası tabanlı bildirim durumu takibi.

Amaç: aynı hisse + aynı olay türü için kısa aralıklarla tekrar tekrar e-posta
gönderilmesini engellemek (spam önleme — pipeline dokümanı bölüm 5.6 "açık
nokta"sı). GitHub Actions üzerinde çalışırken, workflow her koşuda bu dosyayı
repoya geri commit'leyerek durumun sonraki çalıştırmalara taşınmasını sağlar
(bkz. .github/workflows/monitor.yml).
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from config import settings


def load_state() -> dict:
    if not settings.ALERT_STATE_PATH.exists():
        return {}
    try:
        with open(settings.ALERT_STATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_state(state: dict) -> None:
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(settings.ALERT_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, default=str)


def should_alert(state: dict, ticker_code: str, event_key: str, cooldown_minutes: int = settings.ALERT_COOLDOWN_MINUTES) -> bool:
    ticker_state = state.get(ticker_code, {})
    last_ts_str = ticker_state.get(event_key)
    if not last_ts_str:
        return True

    try:
        last_ts = datetime.fromisoformat(last_ts_str)
    except ValueError:
        return True

    return datetime.now(timezone.utc) - last_ts >= timedelta(minutes=cooldown_minutes)


def record_alert(state: dict, ticker_code: str, event_key: str) -> dict:
    state.setdefault(ticker_code, {})[event_key] = datetime.now(timezone.utc).isoformat()
    return state
