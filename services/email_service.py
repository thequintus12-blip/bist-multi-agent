"""
SMTP tabanlı e-posta bildirim servisi.

Gmail gibi çoğu sağlayıcı için "uygulama şifresi" (app password) kullanılması
gerekir; normal hesap şifresi genellikle çalışmaz. Kurulum adımları için
README.md dosyasına bakınız.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings

logger = logging.getLogger(__name__)


class EmailConfigError(Exception):
    """SMTP/e-posta ayarları eksik olduğunda fırlatılır."""


def is_configured() -> bool:
    return bool(settings.SMTP_USER and settings.SMTP_PASSWORD and settings.ALERT_EMAIL_TO)


def send_email(subject: str, html_body: str, to_addr: str | None = None) -> None:
    if not is_configured():
        raise EmailConfigError(
            "E-posta ayarları eksik: SMTP_USER, SMTP_PASSWORD ve ALERT_EMAIL_TO "
            "ortam değişkenlerini/secrets girdilerini tanımlayın."
        )

    recipient = to_addr or settings.ALERT_EMAIL_TO

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.ALERT_EMAIL_FROM
    message["To"] = recipient
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.sendmail(settings.ALERT_EMAIL_FROM, recipient, message.as_string())

    logger.info("Bildirim e-postası gönderildi: %s -> %s", subject, recipient)


def build_alert_email_html(ticker_code: str, company_name: str, triggered_events: list[str], analysis: dict) -> str:
    events_html = "".join(f"<li>{event}</li>" for event in triggered_events)
    app_link = (
        f'<p><a href="{settings.APP_BASE_URL}">Uygulamada detayları görüntüle</a></p>'
        if settings.APP_BASE_URL
        else ""
    )

    news = analysis.get("news_mta_analysis", {})
    technical = analysis.get("technical_analysis", {})

    return f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111;">
        <h2>{ticker_code} — {company_name}</h2>
        <p><strong>Tespit edilen kritik gelişmeler:</strong></p>
        <ul>{events_html}</ul>
        <hr>
        <p><strong>Haber/MTA duyarlılığı:</strong> {news.get('sentiment', '—')}</p>
        <p><strong>Etki notu:</strong> {news.get('impact_note', '—')}</p>
        <p><strong>Teknik trend yorumu:</strong> {technical.get('trend_comment', '—')}</p>
        {app_link}
        <hr>
        <p style="font-size: 12px; color: #666;">{settings.DISCLAIMER_TEXT}</p>
      </body>
    </html>
    """
