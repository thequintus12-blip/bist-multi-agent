"""Arayüzde ve e-posta içeriğinde kullanılan küçük formatlama yardımcıları."""

from __future__ import annotations

from datetime import datetime, timezone


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def format_pct(value: float | None, decimals: int = 2) -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_price(value: float | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f} ₺".replace(",", ".")


def sentiment_label_tr(sentiment: str) -> str:
    mapping = {
        "positive": "Olumlu",
        "neutral": "Nötr",
        "negative": "Olumsuz",
    }
    return mapping.get(sentiment, "Nötr")


def sentiment_color(sentiment: str) -> str:
    mapping = {
        "positive": "#22c55e",  # yeşil
        "neutral": "#94a3b8",   # gri-mavi
        "negative": "#ef4444",  # kırmızı
    }
    return mapping.get(sentiment, "#94a3b8")


def price_change_color(value: float | None) -> str:
    if value is None:
        return "#94a3b8"
    if value > 0:
        return "#22c55e"
    if value < 0:
        return "#ef4444"
    return "#94a3b8"
