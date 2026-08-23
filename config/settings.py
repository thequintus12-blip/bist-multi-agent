"""
Merkezi uygulama ayarları.

Tüm eşik değerleri ve sabitler burada toplanır; böylece "kritik olay" tanımı,
bildirim sıklığı ve uyarı metni tek bir yerden yönetilir (pipeline dokümanındaki
Organizasyon Ajanı'nın "son kontrol noktası" sorumluluğuyla uyumlu).

Ortam değişkenleri hem yerel geliştirmede (.env dosyası, python-dotenv ile) hem de
Streamlit Community Cloud'da (Settings > Secrets, TOML formatında) okunabilir.
GitHub Actions üzerinde çalışan monitor.py için ise Actions "Secrets" bölümünden
ortam değişkeni olarak enjekte edilir.
"""

import json
import os
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ALERT_STATE_PATH = DATA_DIR / "alert_state.json"
TICKERS_CONFIG_PATH = Path(__file__).resolve().parent / "tickers.json"


def _get_secret(key: str, default: str | None = None) -> str | None:
    """Önce Streamlit secrets, sonra ortam değişkeni, sonra varsayılan değeri dener.

    Streamlit çalışma zamanı dışında (ör. monitor.py / GitHub Actions) st.secrets
    erişimi hata verebileceği için sessizce ortam değişkenine düşer.
    """
    try:
        import streamlit as st

        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.environ.get(key, default)


def load_ticker_config() -> dict:
    with open(TICKERS_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_TICKER_CONFIG = load_ticker_config()

# --- Hisse listesi ------------------------------------------------------
TICKERS: list[str] = _TICKER_CONFIG.get("tickers", [])
MARKET_SUFFIX: str = _TICKER_CONFIG.get("market_suffix", ".IS")

# --- Veri / önbellek ------------------------------------------------------
OHLCV_LOOKBACK_PERIOD = "1y"       # yfinance period parametresi
OHLCV_INTERVAL = "1d"
PRICE_CACHE_TTL_SECONDS = 15 * 60  # 15 dakika
NEWS_CACHE_TTL_SECONDS = 15 * 60

# --- Teknik indikatör parametreleri ---------------------------------------
SMA_SHORT_WINDOW = 20
SMA_LONG_WINDOW = 50
EMA_WINDOW = 20
RSI_WINDOW = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
VOLUME_AVG_WINDOW = 20

# --- Kritik olay eşikleri (bildirim tetikleme) ----------------------------
# Bu değerler doküman içinde "açık nokta" olarak işaretlenmiştir; ihtiyaca göre
# ayarlanabilir varsayılanlardır.
VOLUME_SPIKE_THRESHOLD_PCT = 100.0   # 20 günlük ortalamanın %X üzerinde hacim
DAILY_PRICE_CHANGE_THRESHOLD_PCT = 5.0
STRONG_SENTIMENT_SCORE_THRESHOLD = 0.6  # -1..1 aralığında

# Aynı hisse + aynı olay türü için tekrar bildirim göndermeden önce beklenecek süre
ALERT_COOLDOWN_MINUTES = 240  # 4 saat (spam önleme)

# --- E-posta ayarları (ortam değişkeni / secrets üzerinden) ---------------
SMTP_HOST = _get_secret("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_get_secret("SMTP_PORT", "465") or 465)
SMTP_USER = _get_secret("SMTP_USER")
SMTP_PASSWORD = _get_secret("SMTP_PASSWORD")
ALERT_EMAIL_FROM = _get_secret("ALERT_EMAIL_FROM", SMTP_USER)
ALERT_EMAIL_TO = _get_secret("ALERT_EMAIL_TO")

# --- Opsiyonel harici haber API anahtarı (varsayılan: ücretsiz Google News RSS) ---
NEWSAPI_KEY = _get_secret("NEWSAPI_KEY")

# --- Uygulama linki (e-posta bildirimlerinde kullanılacak) ---------------
APP_BASE_URL = _get_secret("APP_BASE_URL", "")

# --- Sabit uyarı metni (her çıktıda görünmeli) ----------------------------
DISCLAIMER_TEXT = (
    "Bu içerik yalnızca bilgilendirme amaçlıdır, yatırım tavsiyesi değildir. "
    "Gösterilen indikatör ve haber özetleri \"gösterge durumu\" niteliğindedir; "
    "al/sat önerisi içermez. Veriler gecikmeli olabilir, yatırım kararlarınızı "
    "vermeden önce güncel ve resmi kaynaklardan teyit ediniz."
)
