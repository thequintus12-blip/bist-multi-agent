"""
Haber ve MTA Analiz Ajanı (pipeline dokümanı bölüm 2.1).

Görev: belirlenen hisseyle ilgili haberleri toplar, tekilleştirir, duyarlılık
(sentiment) analizini yapar ve kısa bir etki notu üretir. MTA verisi için
services.news_provider.fetch_mta_data uzatma noktası kullanılır.
"""

from __future__ import annotations

from services import sentiment
from services.news_provider import NewsItem, deduplicate, fetch_mta_data, get_default_provider


class NewsMTAAgent:
    def __init__(self, provider=None):
        self.provider = provider or get_default_provider()

    def analyze(self, ticker_code: str, company_name: str) -> dict:
        raw_items = self.provider.fetch(ticker_code, company_name)
        items: list[NewsItem] = deduplicate(raw_items)

        mta_data = fetch_mta_data(ticker_code)

        texts = [f"{item.title}. {item.summary}" for item in items]
        agg = sentiment.aggregate_sentiment(texts)

        if not items:
            summary = "Bu hisseyle ilgili güncel haber bulunamadı."
            impact_note = "Değerlendirilecek yeterli haber akışı yok."
        else:
            headline_list = "; ".join(item.title for item in items[:3])
            summary = f"Son öne çıkan başlıklar: {headline_list}"
            if agg["conflicting"]:
                impact_note = (
                    "Haber akışında birbiriyle çelişen olumlu ve olumsuz sinyaller tespit edildi; "
                    "tek yönlü bir yorum yapılmamıştır."
                )
            else:
                impact_note = f"Genel haber duyarlılığı {sentiment.label_from_score(agg['score'])} yönde."

        return {
            "summary": summary,
            "sentiment": agg["sentiment"],
            "impact_note": impact_note,
            "sources": [{"title": i.title, "link": i.link, "source": i.source, "published": i.published} for i in items],
            "conflicting": agg["conflicting"],
            "mta_data": mta_data,  # şu an None; gerçek MTA kaynağı bağlandığında doldurulur
        }
