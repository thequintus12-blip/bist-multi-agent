"""
Fiyat/Hacim (OHLCV) veri sağlayıcı.

Varsayılan olarak yfinance (Yahoo Finance) kullanılır; BIST hisseleri için
sembol sonuna otomatik olarak ".IS" eklenir (config/tickers.json içinde
değiştirilebilir).

Bu modül kasıtlı olarak Streamlit'ten bağımsız tutulmuştur ki hem app.py
(arayüz) hem de monitor.py (GitHub Actions üzerinde çalışan arka plan
izleyicisi) tarafından sorunsuzca kullanılabilsin. Önbellekleme (caching)
çağıran taraf sorumluluğundadır (app.py içinde st.cache_data ile yapılır).
"""

from __future__ import annotations

import logging

import pandas as pd
import yfinance as yf

from config import settings

logger = logging.getLogger(__name__)


class DataFetchError(Exception):
    """OHLCV verisi çekilemediğinde fırlatılır."""


def _yf_symbol(ticker_code: str) -> str:
    return f"{ticker_code.upper()}{settings.MARKET_SUFFIX}"


def fetch_ohlcv(
    ticker_code: str,
    period: str = settings.OHLCV_LOOKBACK_PERIOD,
    interval: str = settings.OHLCV_INTERVAL,
) -> pd.DataFrame:
    """Belirtilen hisse için OHLCV verisini döndürür.

    Veri bulunamazsa veya sembol geçersizse DataFetchError fırlatır; çağıran
    taraf bu durumu kullanıcıya "veri bulunamadı" olarak yansıtmalıdır.
    """
    symbol = _yf_symbol(ticker_code)
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)
    except Exception as exc:  # yfinance/urllib ağ hataları
        raise DataFetchError(f"{symbol} için veri çekilirken hata oluştu: {exc}") from exc

    if df is None or df.empty:
        raise DataFetchError(f"{symbol} için fiyat verisi bulunamadı.")

    df = df.rename(columns=str.title)  # Open/High/Low/Close/Volume garantiye alınır
    return df


def get_company_name(ticker_code: str) -> str:
    """Şirket adını dener; bulunamazsa hisse kodunu döndürür (hard-code isim listesi yok)."""
    symbol = _yf_symbol(ticker_code)
    try:
        info = yf.Ticker(symbol).get_info()
        name = info.get("longName") or info.get("shortName")
        if name:
            return name
    except Exception as exc:
        logger.warning("Şirket adı alınamadı (%s): %s", symbol, exc)
    return ticker_code.upper()


def get_last_price_summary(df: pd.DataFrame) -> dict:
    """Son kapanış, günlük değişim ve tarih bilgisini döndürür."""
    if df.empty:
        return {"last_close": None, "change_pct": None, "last_date": None}

    last_close = float(df["Close"].iloc[-1])
    if len(df) >= 2:
        prev_close = float(df["Close"].iloc[-2])
        change_pct = (last_close - prev_close) / prev_close * 100 if prev_close else None
    else:
        change_pct = None

    return {
        "last_close": last_close,
        "change_pct": change_pct,
        "last_date": df.index[-1].to_pydatetime(),
    }
