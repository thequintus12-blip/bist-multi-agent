"""
Teknik indikatör hesaplamaları.

Harici TA kütüphanelerine (ta-lib gibi derleme gerektiren paketlere) bağımlı
olmamak için tüm indikatörler pandas/numpy ile sıfırdan hesaplanır.

Tüm etiket üretimi fonksiyonları "gösterge durumu" diliyle yazılmıştır;
"al" / "sat" gibi tavsiye niteliğinde ifadeler kasıtlı olarak kullanılmaz
(pipeline dokümanı 2.2 ve 2.3 numaralı bölümlerdeki gereksinim).
"""

from __future__ import annotations

import pandas as pd


def sma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def ema(series: pd.Series, window: int) -> pd.Series:
    return series.ewm(span=window, adjust=False).mean()


def rsi(series: pd.Series, window: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, pd.NA)
    rsi_value = 100 - (100 / (1 + rs))
    return rsi_value.fillna(50)  # veri yetersizse nötr değer


def macd(
    series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9
) -> tuple[pd.Series, pd.Series, pd.Series]:
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def volume_change_pct(df: pd.DataFrame, window: int = 20) -> float | None:
    """Son günün hacmini, önceki N günlük ortalama hacme kıyasla yüzde olarak döndürür."""
    if len(df) < window + 1:
        return None
    avg_volume = df["Volume"].iloc[-(window + 1):-1].mean()
    last_volume = df["Volume"].iloc[-1]
    if not avg_volume or avg_volume == 0:
        return None
    return float((last_volume - avg_volume) / avg_volume * 100)


def detect_candlestick_patterns(df: pd.DataFrame, lookback: int = 2) -> list[str]:
    """Basit kural tabanlı mum formasyonu tespiti (son 1-2 mum üzerinden)."""
    patterns: list[str] = []
    if len(df) < lookback + 1:
        return patterns

    last = df.iloc[-1]
    prev = df.iloc[-2]

    body = abs(last["Close"] - last["Open"])
    candle_range = last["High"] - last["Low"]
    prev_body = abs(prev["Close"] - prev["Open"])

    # Doji: gövde, toplam aralığın çok küçük bir kısmı
    if candle_range > 0 and body / candle_range < 0.1:
        patterns.append("Doji mum formasyonu tespit edildi (kararsızlık göstergesi)")

    # Boğa yutan (bullish engulfing)
    if (
        prev["Close"] < prev["Open"]
        and last["Close"] > last["Open"]
        and last["Close"] >= prev["Open"]
        and last["Open"] <= prev["Close"]
    ):
        patterns.append("Boğa yutan (bullish engulfing) formasyonu tespit edildi")

    # Ayı yutan (bearish engulfing)
    if (
        prev["Close"] > prev["Open"]
        and last["Close"] < last["Open"]
        and last["Open"] >= prev["Close"]
        and last["Close"] <= prev["Open"]
    ):
        patterns.append("Ayı yutan (bearish engulfing) formasyonu tespit edildi")

    # Çekiç (hammer): küçük gövde, uzun alt fitil, üstte kısa/no fitil
    lower_wick = min(last["Open"], last["Close"]) - last["Low"]
    upper_wick = last["High"] - max(last["Open"], last["Close"])
    if candle_range > 0 and body / candle_range < 0.35 and lower_wick > 2 * body and upper_wick < body:
        patterns.append("Çekiç (hammer) mum formasyonu tespit edildi")

    return patterns


def build_signal_labels(
    df: pd.DataFrame,
    sma_short: pd.Series,
    sma_long: pd.Series,
    rsi_series: pd.Series,
    macd_line: pd.Series,
    macd_signal: pd.Series,
    rsi_overbought: float,
    rsi_oversold: float,
    volume_change: float | None,
    volume_spike_threshold: float,
) -> list[str]:
    """Tüm indikatörlerden 'gösterge durumu' etiketleri üretir (tavsiye değildir)."""
    labels: list[str] = []

    last_rsi = rsi_series.iloc[-1]
    if pd.notna(last_rsi):
        if last_rsi >= rsi_overbought:
            labels.append(f"RSI aşırı alım bölgesinde ({last_rsi:.1f}) — gösterge durumu")
        elif last_rsi <= rsi_oversold:
            labels.append(f"RSI aşırı satım bölgesinde ({last_rsi:.1f}) — gösterge durumu")

    if len(macd_line) >= 2 and len(macd_signal) >= 2:
        prev_diff = macd_line.iloc[-2] - macd_signal.iloc[-2]
        last_diff = macd_line.iloc[-1] - macd_signal.iloc[-1]
        if pd.notna(prev_diff) and pd.notna(last_diff):
            if prev_diff < 0 and last_diff > 0:
                labels.append("MACD sinyal çizgisini yukarı kesti (yükseliş kesişimi — gösterge durumu)")
            elif prev_diff > 0 and last_diff < 0:
                labels.append("MACD sinyal çizgisini aşağı kesti (düşüş kesişimi — gösterge durumu)")

    if len(sma_short.dropna()) and len(sma_long.dropna()):
        last_short = sma_short.iloc[-1]
        last_long = sma_long.iloc[-1]
        if pd.notna(last_short) and pd.notna(last_long):
            if last_short > last_long:
                labels.append(
                    f"Kısa vadeli ortalama (SMA{len(sma_short.dropna()) and sma_short.name or ''}) "
                    "uzun vadeli ortalamanın üzerinde — gösterge durumu"
                )
            else:
                labels.append("Kısa vadeli ortalama uzun vadeli ortalamanın altında — gösterge durumu")

    if volume_change is not None and volume_change >= volume_spike_threshold:
        labels.append(f"Hacim, {volume_change:.0f}% ile ortalamanın belirgin üzerinde — gösterge durumu")

    labels.extend(detect_candlestick_patterns(df))

    return labels


def build_trend_comment(sma_short: pd.Series, sma_long: pd.Series, rsi_series: pd.Series) -> str:
    """Kısa, açıklayıcı ve tavsiye içermeyen bir trend yorumu üretir."""
    if sma_short.dropna().empty or sma_long.dropna().empty:
        return "Trend yorumu için yeterli geçmiş veri bulunmuyor."

    last_short = sma_short.iloc[-1]
    last_long = sma_long.iloc[-1]
    last_rsi = rsi_series.iloc[-1] if pd.notna(rsi_series.iloc[-1]) else 50

    if pd.isna(last_short) or pd.isna(last_long):
        return "Trend yorumu için yeterli geçmiş veri bulunmuyor."

    if last_short > last_long and last_rsi >= 50:
        return "Kısa vadeli ortalamalar uzun vadeliye göre güçlü seyrediyor; göstergeler yukarı yönlü bir eğilime işaret ediyor (gösterge durumu, tavsiye değildir)."
    if last_short < last_long and last_rsi <= 50:
        return "Kısa vadeli ortalamalar uzun vadeliye göre zayıf seyrediyor; göstergeler aşağı yönlü bir eğilime işaret ediyor (gösterge durumu, tavsiye değildir)."
    return "Göstergeler karışık sinyaller veriyor; net bir yönlü eğilim gözlenmiyor (gösterge durumu, tavsiye değildir)."
