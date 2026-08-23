"""
Arka plan izleme scripti.

Streamlit Community Cloud arka planda sürekli çalışan görevleri desteklemediği
için "sürekli izleme + kritik olayda e-posta bildirimi" sorumluluğu (pipeline
dokümanı bölüm 5.6) bu bağımsız script ile GitHub Actions cron zamanlayıcısı
üzerinden yürütülür (bkz. .github/workflows/monitor.yml).

Çalıştırma:
    python monitor.py

Gerekli ortam değişkenleri (GitHub Actions Secrets veya yerel .env):
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, ALERT_EMAIL_FROM, ALERT_EMAIL_TO
"""

from __future__ import annotations

import logging
import sys

from agents.orchestrator_agent import OrchestratorAgent
from config import settings
from services import alert_state, email_service
from services.data_provider import DataFetchError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("monitor")


def run() -> int:
    orchestrator = OrchestratorAgent()
    state = alert_state.load_state()

    if not email_service.is_configured():
        logger.warning(
            "E-posta ayarları eksik (SMTP_USER/SMTP_PASSWORD/ALERT_EMAIL_TO). "
            "Kritik olaylar tespit edilecek ama e-posta gönderilmeyecek."
        )

    total_alerts_sent = 0

    for ticker in settings.TICKERS:
        logger.info("İşleniyor: %s", ticker)
        try:
            combined = orchestrator.get_full_analysis(ticker)
        except DataFetchError as exc:
            logger.error("Veri alınamadı (%s): %s", ticker, exc)
            continue
        except Exception:
            logger.exception("Beklenmeyen hata (%s)", ticker)
            continue

        triggered_events = orchestrator.check_critical_events(combined)
        if not triggered_events:
            logger.info("%s için kritik olay tespit edilmedi.", ticker)
            continue

        event_key = "critical_event"
        if not alert_state.should_alert(state, ticker, event_key):
            logger.info("%s için olay var ancak cooldown süresi dolmadı, e-posta atlanıyor.", ticker)
            continue

        logger.info("%s için %d kritik olay tespit edildi: %s", ticker, len(triggered_events), triggered_events)

        if email_service.is_configured():
            try:
                html = email_service.build_alert_email_html(
                    ticker, combined["company_name"], triggered_events, combined
                )
                email_service.send_email(
                    subject=f"[BIST Bildirim] {ticker} için kritik gelişme",
                    html_body=html,
                )
                total_alerts_sent += 1
            except Exception:
                logger.exception("E-posta gönderilemedi (%s)", ticker)
                continue

        state = alert_state.record_alert(state, ticker, event_key)

    alert_state.save_state(state)
    logger.info("Tarama tamamlandı. Gönderilen bildirim sayısı: %d", total_alerts_sent)
    return 0


if __name__ == "__main__":
    sys.exit(run())
