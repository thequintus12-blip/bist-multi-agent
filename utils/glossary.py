"""
Kullanıcı arama çubuğuna bir hisse kodu/adı değil de genel bir finansal terim
yazdığında (pipeline dokümanı 2.3 ve 5.5 numaralı bölümler) kullanılacak basit,
harici API gerektirmeyen bir sözlük.
"""

TERMS_GLOSSARY: dict[str, str] = {
    "rsi": "RSI (Göreceli Güç Endeksi), bir hissenin son dönemdeki fiyat hareketlerinin hızını ve büyüklüğünü 0-100 arasında ölçen bir momentum göstergesidir. 70 üzeri genellikle 'aşırı alım', 30 altı 'aşırı satım' bölgesi olarak yorumlanır.",
    "macd": "MACD (Hareketli Ortalama Yakınsama/Iraksama), iki farklı üstel hareketli ortalama arasındaki farkı kullanarak trend yönü ve momentum hakkında gösterge üreten teknik bir indikatördür.",
    "sma": "SMA (Basit Hareketli Ortalama), belirli bir dönemdeki kapanış fiyatlarının aritmetik ortalamasıdır; kısa vadeli dalgalanmaları yumuşatarak trendi görünür kılar.",
    "ema": "EMA (Üstel Hareketli Ortalama), yakın tarihli fiyatlara daha fazla ağırlık veren bir hareketli ortalama türüdür; SMA'ya göre fiyat değişimlerine daha hızlı tepki verir.",
    "hacim": "İşlem hacmi, belirli bir zaman diliminde el değiştiren hisse adedidir. Ani hacim artışları genellikle önemli bir haber veya gelişmeye işaret edebilir.",
    "temettü": "Temettü, bir şirketin elde ettiği kârın bir kısmının pay sahiplerine nakit veya bedelsiz hisse şeklinde dağıtılmasıdır.",
    "piyasa değeri": "Piyasa değeri (piyasa kapitalizasyonu), bir şirketin toplam pay sayısı ile güncel hisse fiyatının çarpımıyla bulunan toplam borsa değeridir.",
    "f/k oranı": "Fiyat/Kazanç (F/K) oranı, hisse fiyatının şirketin hisse başına kârına bölünmesiyle elde edilir; bir hissenin kazancına göre 'pahalı' veya 'ucuz' görünüp görünmediğine dair bir gösterge sunar.",
    "volatilite": "Volatilite, bir hissenin fiyatındaki dalgalanma derecesidir; yüksek volatilite daha büyük ve hızlı fiyat hareketleri anlamına gelir.",
    "kap": "KAP (Kamuyu Aydınlatma Platformu), Türkiye'de borsaya kote şirketlerin finansal tablo ve önemli açıklamalarını kamuya duyurduğu resmi platformdur.",
    "bist": "BIST (Borsa İstanbul), Türkiye'nin ulusal menkul kıymetler borsasıdır.",
    "candlestick": "Mum grafiği (candlestick), bir zaman aralığındaki açılış, kapanış, en yüksek ve en düşük fiyatları tek bir 'mum' ile gösteren yaygın bir fiyat grafiği türüdür.",
    "yutan formasyon": "Yutan formasyon (engulfing pattern), bir mumun bir öncekini gövdesiyle tamamen kapsadığı ve olası bir trend dönüşüne işaret edebilen bir mum formasyonudur.",
    "doji": "Doji, açılış ve kapanış fiyatlarının birbirine çok yakın olduğu, piyasada kararsızlığa işaret edebilen bir mum formasyonudur.",
    "duyarlılık analizi": "Duyarlılık (sentiment) analizi, haber veya metinlerin olumlu/nötr/olumsuz yönde eğilimini ölçmeye çalışan bir analiz yöntemidir.",
}


def lookup_term(query: str) -> str | None:
    """Sorguyu sözlükte arar; kısmi eşleşmeyi de destekler. Bulunamazsa None döner."""
    q = query.strip().lower()
    if q in TERMS_GLOSSARY:
        return TERMS_GLOSSARY[q]
    for key, definition in TERMS_GLOSSARY.items():
        if q in key or key in q:
            return definition
    return None
