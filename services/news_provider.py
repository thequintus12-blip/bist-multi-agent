"""
Haber ve MTA veri sağlayıcı katmanı.

Pipeline dokümanı, haber/MTA API sağlayıcısının seçimini açık bir nokta
olarak işaretliyor (bkz. bölüm 7). Bu modül, kod değişikliği gerektirmeden
sağlayıcı değiştirilebilecek şekilde küçük bir arayüz (NewsProvider) üzerine
kurulmuştur:

- Varsayılan: GoogleNewsRSSProvider — API anahtarı gerektirmez, Google News
  RSS aramasını kullanır, sadece başlık/özet/kaynak/link döner (tam metin
  kazımaz).
- Genişletme noktası: NEWSAPI_KEY tanımlıysa NewsAPIProvider de kullanılabilir
  (bkz. README "Genişletme Noktaları").

MTA (Menkul Tanıtım Analizi vb. — kurum içi tanıma göre değişebilir) verisi
için ayrı, standart bir kamuya açık API bulunmadığından `fetch_mta_data`
fonksiyonu net bir uzatma noktası olarak bırakılmıştır; gerçek bir MTA veri
kaynağı belirlendiğinde yalnızca bu fonksiyonun içi doldurulmalıdır.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import quote_plus

import feedparser
import requests

from config import settings

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (compatible; BISTAnalizBot/1.0)"


@dataclass
class NewsItem:
    title: str
    link: str
    source: str
    published: str
    summary: str = ""


class NewsProvider:
    """Haber sağlayıcılar için ortak arayüz."""

    def fetch(self, ticker_code: str, company_name: str, max_items: int = 8) -> list[NewsItem]:
        raise NotImplementedError


class GoogleNewsRSSProvider(NewsProvider):
    """Ücretsiz, API anahtarı gerektirmeyen Google News RSS tabanlı sağlayıcı."""

    BASE_URL = "https://news.google.com/rss/search"

    def fetch(self, ticker_code: str, company_name: str, max_items: int = 8) -> list[NewsItem]:
        query = f"{company_name} {ticker_code} hisse BIST"
        url = f"{self.BASE_URL}?q={quote_plus(query)}&hl=tr&gl=TR&ceid=TR:tr"

        try:
            response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=10)
            response.raise_for_status()
        except Exception as exc:
            logger.warning("Google News RSS alınamadı (%s): %s", ticker_code, exc)
            return []

        parsed = feedparser.parse(response.content)
        items: list[NewsItem] = []
        for entry in parsed.entries[:max_items]:
            items.append(
                NewsItem(
                    title=getattr(entry, "title", "").strip(),
                    link=getattr(entry, "link", ""),
                    source=getattr(getattr(entry, "source", None), "title", "Google News"),
                    published=getattr(entry, "published", ""),
                    summary=getattr(entry, "summary", ""),
                )
            )
        return items


def deduplicate(items: list[NewsItem]) -> list[NewsItem]:
    """Aynı/çok benzer başlıkları tekilleştirir (basit normalize + set kontrolü)."""
    seen: set[str] = set()
    unique: list[NewsItem] = []
    for item in items:
        key = "".join(ch.lower() for ch in item.title if ch.isalnum())
        if key and key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def get_default_provider() -> NewsProvider:
    return GoogleNewsRSSProvider()


def fetch_mta_data(ticker_code: str) -> dict | None:
    """MTA verisi için uzatma noktası (genişletme noktası).

    Kurum/kapsam içinde standart bir MTA API'si belirlendiğinde bu fonksiyon
    gerçek çağrıyı yapacak şekilde doldurulmalıdır. Şimdilik None döner ve
    çağıran taraf (NewsMTAAgent) bunu "MTA verisi mevcut değil" olarak
    ele alır; uygulamanın geri kalanı etkilenmez.
    """
    return None
