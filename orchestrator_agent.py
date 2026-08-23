"""
Organizasyon Ajanı / Yönetici Ajan (pipeline dokümanı bölüm 2.3).

Sorumluluklar:
- Sorgu ayrıştırma (hisse kodu / hisse adı / genel finansal terim).
- Haber+MTA ve Teknik İndikatör ajanlarının çıktısını tek bir yapıda birleştirme.
- Çelişkili sinyalleri açıkça işaretleme (gizlememe).
- Kritik olay/eşik tespiti (bildirim tetikleme mantığı için).
- Yatırım tavsiyesi içermeyen dil kullanımının son kontrolü.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from config import settings
from services import data_provider
from utils.formatting import now_iso
from utils.glossary import lookup_term

from .news_mta_agent import NewsMTAAgent
from .technical_agent import TechnicalAgent

# Son kontrol noktası: bu ifadeler doğrudan tavsiye niteliği taşıdığı için
# üretilen metinlerde bulunmamalıdır. Bulunursa nötr bir ifadeyle değiştirilir.
_ADVICE_PATTERNS = [
    (re.compile(r"\bal(ınmalı|ın|ması gerek)?\b", re.IGNORECASE), "gösterge durumu"),
    (re.compile(r"\bsat(ılmalı|ın|ması gerek)?\b", re.IGNORECASE), "gösterge durumu"),
    (re.compile(r"tavsiye ederim", re.IGNORECASE), "bilgilendirme amaçlıdır"),
]


class OrchestratorAgent:
    def __init__(self, news_agent: NewsMTAAgent | None = None, technical_agent: TechnicalAgent | None = None):
        self.news_agent = news_agent or NewsMTAAgent()
        self.technical_agent = technical_agent or TechnicalAgent()

    # ------------------------------------------------------------------
    # Sorgu ayrıştırma
    # ------------------------------------------------------------------
    def resolve_query(self, query: str) -> dict:
        """Sorguyu hisse kodu / hisse adı / genel terim olarak sınıflandırır.

        Dönüş: {"type": "ticker"|"term"|"unknown", "ticker": str|None, "term_definition": str|None}
        """
        q = query.strip()
        if not q:
            return {"type": "unknown", "ticker": None, "term_definition": None}

        upper_q = q.upper()
        if upper_q in settings.TICKERS:
            return {"type": "ticker", "ticker": upper_q, "term_definition": None}

        # Şirket adına göre eşleşme (önbelleklenmiş isimler üzerinden)
        for ticker in settings.TICKERS:
            name = data_provider.get_company_name(ticker)
            if q.lower() in name.lower():
                return {"type": "ticker", "ticker": ticker, "term_definition": None}

        term_definition = lookup_term(q)
        if term_definition:
            return {"type": "term", "ticker": None, "term_definition": term_definition}

        return {"type": "unknown", "ticker": None, "term_definition": None}

    # ------------------------------------------------------------------
    # Birleşik analiz
    # ------------------------------------------------------------------
    def get_full_analysis(self, ticker_code: str) -> dict:
        company_name = data_provider.get_company_name(ticker_code)
        news_result = self.news_agent.analyze(ticker_code, company_name)
        technical_result = self.technical_agent.analyze(ticker_code)

        combined = {
            "ticker": ticker_code,
            "company_name": company_name,
            "news_mta_analysis": news_result,
            "technical_analysis": technical_result,
            "last_updated": now_iso(),
            "disclaimer": settings.DISCLAIMER_TEXT,
        }

        combined["conflict_notes"] = self._detect_conflicts(news_result, technical_result)
        combined = self._enforce_no_advice_language(combined)
        return combined

    def _detect_conflicts(self, news_result: dict, technical_result: dict) -> list[str]:
        notes: list[str] = []
        if news_result.get("conflicting"):
            notes.append("Haber akışı içinde birbiriyle çelişen sinyaller var.")

        news_sentiment = news_result.get("sentiment")
        trend_comment = technical_result.get("trend_comment", "")
        if news_sentiment == "positive" and "aşağı yönlü" in trend_comment:
            notes.append("Olumlu haber duyarlılığına karşın teknik görünüm zayıflıyor — çelişkili sinyal.")
        elif news_sentiment == "negative" and "yukarı yönlü" in trend_comment:
            notes.append("Olumsuz haber duyarlılığına karşın teknik görünüm güçleniyor — çelişkili sinyal.")

        return notes

    def _enforce_no_advice_language(self, combined: dict) -> dict:
        """Metin alanlarını tavsiye ifadeleri için tarar ve nötrleştirir (son kontrol noktası)."""
        text_paths = [
            ("news_mta_analysis", "summary"),
            ("news_mta_analysis", "impact_note"),
            ("technical_analysis", "trend_comment"),
        ]
        for section, field in text_paths:
            value = combined.get(section, {}).get(field)
            if isinstance(value, str):
                for pattern, replacement in _ADVICE_PATTERNS:
                    value = pattern.sub(replacement, value)
                combined[section][field] = value
        return combined

    # ------------------------------------------------------------------
    # Kritik olay tespiti (bildirim tetikleme için)
    # ------------------------------------------------------------------
    def check_critical_events(self, combined: dict) -> list[str]:
        events: list[str] = []
        technical = combined.get("technical_analysis", {})
        news = combined.get("news_mta_analysis", {})

        volume_change = technical.get("indicators", {}).get("volume_change_pct")
        if volume_change is not None and volume_change >= settings.VOLUME_SPIKE_THRESHOLD_PCT:
            events.append(f"Ani hacim artışı: ortalamanın {volume_change:.0f}% üzerinde.")

        price_summary = technical.get("price_summary", {})
        change_pct = price_summary.get("change_pct")
        if change_pct is not None and abs(change_pct) >= settings.DAILY_PRICE_CHANGE_THRESHOLD_PCT:
            direction = "yükseliş" if change_pct > 0 else "düşüş"
            events.append(f"Günlük %{abs(change_pct):.1f} {direction} — belirlenen eşiğin üzerinde.")

        rsi = technical.get("indicators", {}).get("rsi")
        if rsi is not None:
            if rsi >= settings.RSI_OVERBOUGHT:
                events.append(f"RSI aşırı alım bölgesine girdi ({rsi:.1f}).")
            elif rsi <= settings.RSI_OVERSOLD:
                events.append(f"RSI aşırı satım bölgesine girdi ({rsi:.1f}).")

        news_score = None
        if news.get("sentiment") in ("positive", "negative") and news.get("sources"):
            # Yaklaşık skor: aggregate_sentiment sadece agent içinde hesaplanıyor,
            # burada eşik kontrolü için etiketi kullanmak yeterli basit bir varsayımdır.
            news_score = 1.0 if news["sentiment"] == "positive" else -1.0

        if news_score is not None and abs(news_score) >= settings.STRONG_SENTIMENT_SCORE_THRESHOLD:
            direction = "olumlu" if news_score > 0 else "olumsuz"
            events.append(f"Güçlü {direction} haber duyarlılığı tespit edildi.")

        if combined.get("conflict_notes"):
            events.append("Haber ve teknik görünüm arasında çelişki tespit edildi — dikkatli inceleyin.")

        return events
