"""
Basit, kural/sözlük tabanlı Türkçe finansal duyarlılık (sentiment) analizi.

Harici bir ML servisi veya API anahtarı gerektirmez; bu haliyle şeffaf ve
ücretsiz bir varsayılan sağlar. Daha gelişmiş bir analiz isteniyorsa bu
modülün arayüzü (score_text / aggregate) korunarak bir LLM ya da özel bir
sentiment API'si ile değiştirilebilir (bkz. README "Genişletme Noktaları").
"""

from __future__ import annotations

import re

POSITIVE_WORDS = [
    "artış", "arttı", "artıyor", "yükseliş", "yükseldi", "yükseliyor", "rekor",
    "kâr", "kar", "kazanç", "büyüme", "büyüdü", "güçlü", "olumlu", "iyileşme",
    "anlaşma", "sözleşme", "ihracat", "yatırım", "genişleme", "başarı",
    "hedef fiyat yükseltildi", "temettü", "kapasite artışı", "yeni ihale",
    "prim", "toparlanma", "pozitif",
]

NEGATIVE_WORDS = [
    "düşüş", "düştü", "düşüyor", "gerileme", "geriledi", "zarar", "kayıp",
    "kriz", "olumsuz", "resesyon", "iflas", "dava", "soruşturma", "ceza",
    "iptal", "gecikme", "durdurma", "negatif", "hedef fiyat düşürüldü",
    "satış baskısı", "değer kaybı", "küçülme", "işten çıkarma", "zayıflama",
]

_WORD_RE = re.compile(r"[a-zçğıöşü]+", re.IGNORECASE)


def score_text(text: str) -> float:
    """Metni -1 (çok olumsuz) ile +1 (çok olumlu) arasında bir skora eşler."""
    if not text:
        return 0.0

    lowered = text.lower()
    pos_hits = sum(lowered.count(word) for word in POSITIVE_WORDS)
    neg_hits = sum(lowered.count(word) for word in NEGATIVE_WORDS)

    total = pos_hits + neg_hits
    if total == 0:
        return 0.0
    return (pos_hits - neg_hits) / total


def label_from_score(score: float) -> str:
    if score > 0.15:
        return "positive"
    if score < -0.15:
        return "negative"
    return "neutral"


def aggregate_sentiment(texts: list[str]) -> dict:
    """Birden fazla haber başlığı/özeti için toplu duyarlılık ve çelişki tespiti."""
    if not texts:
        return {"sentiment": "neutral", "score": 0.0, "conflicting": False}

    scores = [score_text(t) for t in texts]
    avg_score = sum(scores) / len(scores)

    has_strong_positive = any(s > 0.4 for s in scores)
    has_strong_negative = any(s < -0.4 for s in scores)
    conflicting = has_strong_positive and has_strong_negative

    return {
        "sentiment": label_from_score(avg_score),
        "score": round(avg_score, 3),
        "conflicting": conflicting,
    }
