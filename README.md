# BIST Çok Ajanlı Finansal Analiz ve Bildirim Uygulaması

Bu proje, `bist-cok-ajan-finansal-analiz-pipeline.md` dokümanında tanımlanan
üç ajanlı mimarinin (Haber ve MTA Analiz Ajanı, Teknik İndikatör Analiz
Ajanı, Organizasyon Ajanı) çalışan bir uygulamaya dönüştürülmüş halidir.

**Yatırım tavsiyesi vermez.** Tüm çıktılar yalnızca bilgilendirme amaçlıdır.

## Mimari Özeti

```
app.py (Streamlit arayüzü — arama çubuğu + genel bakış)
monitor.py (GitHub Actions cron — sürekli izleme + e-posta bildirimi)
        │
        ▼
agents/orchestrator_agent.py  ← agents/news_mta_agent.py
                               ← agents/technical_agent.py
        │
        ▼
services/  (veri, haber, duyarlılık, e-posta, bildirim durumu)
utils/     (indikatör hesaplama, formatlama, terim sözlüğü)
config/    (settings.py, tickers.json)
```

İki temas noktası ayrı ayrı çalışır:

- **Arama çubuğu** → `app.py` (Streamlit), talep üzerine anlık analiz.
- **E-posta bildirimi** → `monitor.py`, GitHub Actions üzerinde zamanlanmış
  olarak çalışır (Streamlit Community Cloud arka planda sürekli görev
  çalıştırmayı desteklemediği için bu iş GitHub Actions'a taşınmıştır).

## Kurulum (Yerel Geliştirme)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # ve .env içindeki değerleri doldurun
streamlit run app.py
```

## GitHub'a Yükleme

```bash
git init
git add .
git commit -m "İlk sürüm: BIST çok ajanlı analiz uygulaması"
git branch -M main
git remote add origin https://github.com/<kullanici-adiniz>/<repo-adi>.git
git push -u origin main
```

> `.env` ve `.streamlit/secrets.toml` dosyaları `.gitignore` içinde
> hariç tutulmuştur — gerçek şifre/anahtarlarınız asla repoya gitmez.

## Streamlit Community Cloud'a Deploy

1. [share.streamlit.io](https://share.streamlit.io) üzerinden GitHub
   hesabınızla giriş yapın.
2. "New app" → deponuzu ve `app.py` dosyasını seçin.
3. **App settings → Secrets** bölümüne `.streamlit/secrets.toml.example`
   dosyasındaki alanları gerçek değerlerle doldurup yapıştırın.
4. Deploy edin. Uygulama her push sonrası otomatik güncellenir.

## GitHub Actions ile Otomatik İzleme (E-posta Bildirimleri)

1. Repo → **Settings → Secrets and variables → Actions** bölümüne şu
   secret'ları ekleyin: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`,
   `SMTP_PASSWORD`, `ALERT_EMAIL_FROM`, `ALERT_EMAIL_TO` (opsiyonel:
   `NEWSAPI_KEY`, `APP_BASE_URL`).
2. `.github/workflows/monitor.yml` iş akışı hafta içi BIST işlem saatlerinde
   (yaklaşık 07:00–15:00 UTC) 30 dakikada bir otomatik çalışır; **Actions**
   sekmesinden "Run workflow" ile manuel de tetikleyebilirsiniz.
3. Kritik bir olay tespit edildiğinde e-posta gönderilir ve
   `data/alert_state.json` dosyası (spam önleme/cooldown durumu) otomatik
   olarak commit'lenir.

### Gmail ile SMTP kullanıyorsanız

Normal hesap şifreniz çalışmaz; Google hesabınızda 2 adımlı doğrulamayı
açıp bir **"Uygulama Şifresi" (App Password)** oluşturmanız ve
`SMTP_PASSWORD` olarak onu kullanmanız gerekir.

## Hisse Listesini Değiştirme

`config/tickers.json` dosyasını düzenleyin — kod değişikliği gerekmez:

```json
{
  "market_suffix": ".IS",
  "tickers": ["ASELS", "TUPRS", "..."]
}
```

## Kritik Olay Eşiklerini Ayarlama

`config/settings.py` içindeki şu sabitler ihtiyaca göre değiştirilebilir
(doküman bölüm 7'de "netleştirilmesi gereken" olarak işaretlenmiş
varsayılanlardır):

| Sabit | Varsayılan | Açıklama |
|---|---|---|
| `VOLUME_SPIKE_THRESHOLD_PCT` | 100 | Ortalama hacmin üzerindeki artış yüzdesi |
| `DAILY_PRICE_CHANGE_THRESHOLD_PCT` | 5 | Günlük fiyat değişim eşiği |
| `RSI_OVERBOUGHT` / `RSI_OVERSOLD` | 70 / 30 | RSI aşırı alım/satım seviyeleri |
| `STRONG_SENTIMENT_SCORE_THRESHOLD` | 0.6 | Güçlü haber duyarlılığı eşiği |
| `ALERT_COOLDOWN_MINUTES` | 240 | Aynı olay için tekrar bildirim göndermeden önce beklenecek süre |

## Veri Kaynakları (Varsayılanlar)

Pipeline dokümanı, API sağlayıcı seçimini açık bir nokta olarak
işaretliyor (bölüm 7). Bu uygulama, anahtar gerektirmeyen/ücretsiz
varsayılanlarla **çalışır durumda** teslim edilir; ihtiyaca göre
değiştirilebilir:

- **Fiyat/Hacim (OHLCV):** [yfinance](https://pypi.org/project/yfinance/)
  (Yahoo Finance) — `services/data_provider.py`.
- **Haberler:** Google News RSS (ücretsiz, anahtarsız) —
  `services/news_provider.py` içindeki `GoogleNewsRSSProvider`.
- **MTA verisi:** Standart, kamuya açık bir API belirtilmediği için
  `services/news_provider.fetch_mta_data()` bir uzatma noktası olarak
  bırakılmıştır; gerçek kaynak belirlendiğinde yalnızca bu fonksiyon
  doldurulmalıdır.
- **Duyarlılık analizi:** Basit, şeffaf, kural/sözlük tabanlı Türkçe
  finansal terim skorlayıcı — `services/sentiment.py`.

### Genişletme Noktaları

- Yeni bir haber sağlayıcısı eklemek için `services/news_provider.py`
  içinde `NewsProvider` sınıfından türeyen yeni bir sınıf yazıp
  `get_default_provider()` fonksiyonunu güncelleyin.
- Daha gelişmiş bir duyarlılık analizi (ör. bir LLM API'si) için
  `services/sentiment.py` içindeki `score_text` / `aggregate_sentiment`
  arayüzünü koruyarak implementasyonu değiştirin.

## Proje Yapısı

```
app.py                          Streamlit arayüzü (arama çubuğu, genel bakış, bildirim günlüğü)
monitor.py                      GitHub Actions ile çalışan izleme/bildirim scripti
agents/
  news_mta_agent.py              Haber ve MTA Analiz Ajanı
  technical_agent.py             Teknik İndikatör Analiz Ajanı
  orchestrator_agent.py          Organizasyon Ajanı (birleştirme, sorgu, kritik olay tespiti)
services/
  data_provider.py               OHLCV veri çekme (yfinance)
  news_provider.py               Haber çekme + MTA uzatma noktası
  sentiment.py                   Kural tabanlı duyarlılık analizi
  email_service.py               SMTP e-posta gönderimi
  alert_state.py                 Bildirim geçmişi / cooldown (spam önleme)
utils/
  indicators.py                  SMA/EMA/RSI/MACD/hacim/mum formasyonu hesaplama
  formatting.py                  Görüntüleme yardımcıları
  glossary.py                    Genel finansal terim sözlüğü
config/
  settings.py                    Merkezi ayarlar ve eşik değerleri
  tickers.json                   İzlenen hisse listesi
.github/workflows/monitor.yml    Zamanlanmış izleme iş akışı
.streamlit/config.toml           Koyu tema ayarları
```

## Bilinen Sınırlamalar / Sonraki Adımlar

- MTA verisi için gerçek bir kaynak henüz entegre edilmedi (bkz.
  "Genişletme Noktaları").
- Duyarlılık analizi kural tabanlıdır; yüksek hacimli/karmaşık haber
  metinlerinde daha gelişmiş bir modelle değiştirilmesi önerilir.
- Kritik olay eşikleri makul varsayılanlardır; canlı kullanım öncesi
  gözden geçirilmelidir.
- Veriler (fiyat ve haber) gecikmeli olabilir; uygulama bunu arayüzde
  ve e-postalarda açıkça belirtir.
