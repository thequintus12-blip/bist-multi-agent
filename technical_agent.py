"""
Teknik İndikatör Analiz Ajanı (pipeline dokümanı bölüm 2.2).

Görev: OHLCV verisinden SMA/EMA/RSI/MACD/hacim değişimi ve mum formasyonlarını
hesaplar; yalnızca "gösterge durumu" niteliğinde etiketler üretir (al/sat
tavsiyesi vermez).
"""

from __future__ import annotations

import pandas as pd

from config import settings
from services import data_provider
from utils import indicators


class TechnicalAgent:
    def analyze(self, ticker_code: str) -> dict:
        df: pd.DataFrame = data_provider.fetch_ohlcv(ticker_code)

        close = df["Close"]
        sma_short = indicators.sma(close, settings.SMA_SHORT_WINDOW)
        sma_long = indicators.sma(close, settings.SMA_LONG_WINDOW)
        ema_short = indicators.ema(close, settings.EMA_WINDOW)
        rsi_series = indicators.rsi(close, settings.RSI_WINDOW)
        macd_line, macd_signal, macd_hist = indicators.macd(
            close, settings.MACD_FAST, settings.MACD_SLOW, settings.MACD_SIGNAL
        )
        volume_change = indicators.volume_change_pct(df, settings.VOLUME_AVG_WINDOW)

        signal_labels = indicators.build_signal_labels(
            df=df,
            sma_short=sma_short,
            sma_long=sma_long,
            rsi_series=rsi_series,
            macd_line=macd_line,
            macd_signal=macd_signal,
            rsi_overbought=settings.RSI_OVERBOUGHT,
            rsi_oversold=settings.RSI_OVERSOLD,
            volume_change=volume_change,
            volume_spike_threshold=settings.VOLUME_SPIKE_THRESHOLD_PCT,
        )
        trend_comment = indicators.build_trend_comment(sma_short, sma_long, rsi_series)

        price_summary = data_provider.get_last_price_summary(df)

        return {
            "indicators": {
                "sma_short": _last_or_none(sma_short),
                "sma_long": _last_or_none(sma_long),
                "ema": _last_or_none(ema_short),
                "rsi": _last_or_none(rsi_series),
                "macd": {
                    "line": _last_or_none(macd_line),
                    "signal": _last_or_none(macd_signal),
                    "histogram": _last_or_none(macd_hist),
                },
                "volume_change_pct": volume_change,
            },
            "signal_labels": signal_labels,
            "trend_comment": trend_comment,
            "price_summary": price_summary,
            # Grafik çizimi için ham seriler (app.py tarafından kullanılır)
            "series": {
                "df": df,
                "sma_short": sma_short,
                "sma_long": sma_long,
                "rsi": rsi_series,
                "macd_line": macd_line,
                "macd_signal": macd_signal,
                "macd_hist": macd_hist,
            },
        }


def _last_or_none(series: pd.Series) -> float | None:
    if series is None or series.dropna().empty:
        return None
    value = series.iloc[-1]
    return float(value) if pd.notna(value) else None
