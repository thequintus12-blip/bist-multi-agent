"""
BIST Finansal Analiz ve Bildirim Uygulaması — Streamlit arayüzü.

Bu dosya, pipeline dokümanındaki Organizasyon Ajanı'nın kullanıcıya sunduğu
iki temas noktasından birini (arama çubuğu) uygular. E-posta bildirimleri
ise monitor.py + GitHub Actions üzerinden ayrıca yürütülür (bkz. README.md).
"""

from __future__ import annotations

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from agents.orchestrator_agent import OrchestratorAgent
from config import settings
from services import alert_state, data_provider
from services.data_provider import DataFetchError
from utils.formatting import (
    format_pct,
    format_price,
    now_iso,
    price_change_color,
    sentiment_color,
    sentiment_label_tr,
)

st.set_page_config(
    page_title="BIST Çok Ajanlı Finansal Analiz",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ----------------------------------------------------------------------------
# Stil (dark fintech tema)
# ----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp { background: radial-gradient(circle at 10% 0%, #131a2b 0%, #0b0f19 55%, #090c14 100%); }
    .metric-card {
        background: linear-gradient(160deg, rgba(255,255,255,0.04), rgba(255,255,255,0.01));
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 14px;
        padding: 18px 20px;
        transition: border-color 0.2s ease;
    }
    .metric-card:hover { border-color: rgba(99,179,237,0.5); }
    .badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 600;
        margin: 3px 6px 3px 0;
        color: #0b0f19;
    }
    .badge-neutral {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 999px;
        font-size: 0.8rem;
        margin: 3px 6px 3px 0;
        background: rgba(148,163,184,0.15);
        color: #cbd5e1;
        border: 1px solid rgba(148,163,184,0.3);
    }
    .disclaimer-box {
        background: rgba(148,163,184,0.08);
        border-left: 3px solid #64748b;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 0.82rem;
        color: #94a3b8;
        margin-top: 14px;
    }
    .conflict-box {
        background: rgba(234,179,8,0.10);
        border-left: 3px solid #eab308;
        padding: 10px 14px;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #fde68a;
        margin: 10px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource
def get_orchestrator() -> OrchestratorAgent:
    return OrchestratorAgent()


@st.cache_data(ttl=settings.PRICE_CACHE_TTL_SECONDS, show_spinner=False)
def cached_full_analysis(ticker_code: str) -> dict:
    orchestrator = get_orchestrator()
    return orchestrator.get_full_analysis(ticker_code)


@st.cache_data(ttl=settings.PRICE_CACHE_TTL_SECONDS, show_spinner=False)
def cached_company_name(ticker_code: str) -> str:
    return data_provider.get_company_name(ticker_code)


def render_badges(labels: list[str], color: str) -> None:
    html = "".join(f'<span class="badge" style="background:{color};">{label}</span>' for label in labels)
    st.markdown(html or '<span class="badge-neutral">Belirgin sinyal yok</span>', unsafe_allow_html=True)


def render_price_chart(technical: dict) -> None:
    series = technical["series"]
    df = series["df"]

    fig = make_subplots(
        rows=3,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.55, 0.2, 0.25],
        vertical_spacing=0.03,
        subplot_titles=("Fiyat (Mum Grafiği)", "Hacim", "RSI"),
    )

    fig.add_trace(
        go.Candlestick(
            x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
            increasing_line_color="#22c55e", decreasing_line_color="#ef4444",
            name="Fiyat",
        ),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=series["sma_short"], name=f"SMA{settings.SMA_SHORT_WINDOW}",
                    line=dict(color="#38bdf8", width=1.3)),
        row=1, col=1,
    )
    fig.add_trace(
        go.Scatter(x=df.index, y=series["sma_long"], name=f"SMA{settings.SMA_LONG_WINDOW}",
                    line=dict(color="#f472b6", width=1.3)),
        row=1, col=1,
    )

    volume_colors = ["#22c55e" if c >= o else "#ef4444" for o, c in zip(df["Open"], df["Close"])]
    fig.add_trace(
        go.Bar(x=df.index, y=df["Volume"], name="Hacim", marker_color=volume_colors, opacity=0.7),
        row=2, col=1,
    )

    fig.add_trace(
        go.Scatter(x=df.index, y=series["rsi"], name="RSI", line=dict(color="#a78bfa", width=1.4)),
        row=3, col=1,
    )
    fig.add_hline(y=settings.RSI_OVERBOUGHT, line_dash="dot", line_color="#ef4444", row=3, col=1)
    fig.add_hline(y=settings.RSI_OVERSOLD, line_dash="dot", line_color="#22c55e", row=3, col=1)

    fig.update_layout(
        height=680,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_rangeslider_visible=False,
    )
    st.plotly_chart(fig, use_container_width=True)


def render_macd_chart(technical: dict) -> None:
    series = technical["series"]
    df = series["df"]
    hist_colors = ["#22c55e" if v >= 0 else "#ef4444" for v in series["macd_hist"].fillna(0)]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=df.index, y=series["macd_hist"], name="Histogram", marker_color=hist_colors, opacity=0.6))
    fig.add_trace(go.Scatter(x=df.index, y=series["macd_line"], name="MACD", line=dict(color="#38bdf8", width=1.5)))
    fig.add_trace(go.Scatter(x=df.index, y=series["macd_signal"], name="Sinyal", line=dict(color="#f97316", width=1.5)))
    fig.update_layout(
        height=260,
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_disclaimer() -> None:
    st.markdown(f'<div class="disclaimer-box">⚠️ {settings.DISCLAIMER_TEXT}</div>', unsafe_allow_html=True)


def render_ticker_analysis(ticker_code: str) -> None:
    try:
        with st.spinner(f"{ticker_code} için veriler analiz ediliyor..."):
            combined = cached_full_analysis(ticker_code)
    except DataFetchError as exc:
        st.error(f"Veri alınamadı: {exc}")
        return

    technical = combined["technical_analysis"]
    news = combined["news_mta_analysis"]
    price = technical["price_summary"]

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.markdown(f"### {combined['ticker']} — {combined['company_name']}")
        st.caption(f"Son güncelleme: {combined['last_updated']}")
    with col2:
        st.metric("Son Kapanış", format_price(price.get("last_close")))
    with col3:
        change = price.get("change_pct")
        st.metric("Günlük Değişim", format_pct(change), delta=format_pct(change) if change is not None else None)

    if combined.get("conflict_notes"):
        for note in combined["conflict_notes"]:
            st.markdown(f'<div class="conflict-box">⚡ {note}</div>', unsafe_allow_html=True)

    tab_chart, tab_technical, tab_news = st.tabs(["📈 Grafik", "🧮 Teknik Gösterge Durumu", "📰 Haber & MTA"])

    with tab_chart:
        render_price_chart(technical)
        render_macd_chart(technical)

    with tab_technical:
        st.markdown("**Gösterge Durumu Etiketleri** _(al/sat tavsiyesi değildir)_")
        render_badges(technical["signal_labels"], color="#334155")
        st.markdown("**Trend Yorumu**")
        st.write(technical["trend_comment"])
        with st.expander("Ham indikatör değerleri"):
            ind = technical["indicators"]
            st.json(
                {
                    "sma_short": ind["sma_short"],
                    "sma_long": ind["sma_long"],
                    "ema": ind["ema"],
                    "rsi": ind["rsi"],
                    "macd": ind["macd"],
                    "volume_change_pct": ind["volume_change_pct"],
                }
            )

    with tab_news:
        badge_color = sentiment_color(news["sentiment"])
        st.markdown(
            f'<span class="badge" style="background:{badge_color};">{sentiment_label_tr(news["sentiment"])}</span>',
            unsafe_allow_html=True,
        )
        st.write(news["summary"])
        st.caption(news["impact_note"])
        if news["sources"]:
            st.markdown("**Kaynaklar**")
            for src in news["sources"]:
                st.markdown(f"- [{src['title']}]({src['link']}) — _{src['source']}_")
        else:
            st.info("Şu anda bu hisseyle ilgili güncel haber bulunamadı.")

    render_disclaimer()


def render_search_tab() -> None:
    st.markdown("#### Hisse kodu, şirket adı veya finansal terim yazın")
    query = st.text_input(
        "Arama",
        placeholder="Örn: ASELS, Tüpraş, RSI...",
        label_visibility="collapsed",
    )

    st.caption("İzlenen hisseler: " + ", ".join(settings.TICKERS))

    if not query:
        return

    orchestrator = get_orchestrator()
    resolution = orchestrator.resolve_query(query)

    if resolution["type"] == "ticker":
        render_ticker_analysis(resolution["ticker"])
    elif resolution["type"] == "term":
        st.markdown(f"**{query}** için tanım:")
        st.info(resolution["term_definition"])
    else:
        st.warning(
            "Sorgunuz izlenen hisseler veya bilinen finansal terimler arasında eşleşmedi. "
            "Aşağıdaki hisselerden birini deneyebilirsiniz:"
        )
        st.write(", ".join(settings.TICKERS))


def render_overview_tab() -> None:
    st.markdown("#### Tüm izlenen hisselere genel bakış")
    refresh = st.button("🔄 Tümünü Yenile", help="Önbelleği temizleyip tüm hisseleri yeniden çeker")
    if refresh:
        cached_full_analysis.clear()

    cols = st.columns(3)
    for idx, ticker in enumerate(settings.TICKERS):
        col = cols[idx % 3]
        with col:
            with st.container(border=True):
                try:
                    combined = cached_full_analysis(ticker)
                except DataFetchError:
                    st.markdown(f"**{ticker}**")
                    st.caption("Veri alınamadı")
                    continue

                price = combined["technical_analysis"]["price_summary"]
                change = price.get("change_pct")
                news_sentiment = combined["news_mta_analysis"]["sentiment"]

                st.markdown(f"**{ticker}** · {combined['company_name']}")
                st.markdown(
                    f"<span style='color:{price_change_color(change)}; font-weight:600;'>"
                    f"{format_price(price.get('last_close'))} ({format_pct(change)})</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<span class="badge" style="background:{sentiment_color(news_sentiment)};">'
                    f"{sentiment_label_tr(news_sentiment)} haber</span>",
                    unsafe_allow_html=True,
                )
                if combined.get("conflict_notes"):
                    st.caption("⚡ Çelişkili sinyal tespit edildi")

    render_disclaimer()


def render_alert_log_tab() -> None:
    st.markdown("#### Bildirim Günlüğü")
    st.caption(
        "Sürekli izleme ve kritik olay bildirimleri GitHub Actions üzerinde zamanlanmış "
        "`monitor.py` scripti tarafından yürütülür (bu arayüz sadece son durumu gösterir). "
        "Kurulum için README.md → 'GitHub Actions ile Otomatik İzleme' bölümüne bakın."
    )

    state = alert_state.load_state()
    if not state:
        st.info("Henüz kaydedilmiş bir bildirim yok.")
        return

    rows = []
    for ticker, events in state.items():
        for event_key, ts in events.items():
            rows.append({"Hisse": ticker, "Olay Türü": event_key, "Son Bildirim (UTC)": ts})

    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_sidebar() -> None:
    with st.sidebar:
        st.markdown("## 📈 BIST Çok Ajanlı Analiz")
        st.caption("Haber/MTA Ajanı · Teknik İndikatör Ajanı · Organizasyon Ajanı")
        st.divider()
        st.markdown("**İzlenen Hisseler**")
        st.write(", ".join(settings.TICKERS))
        st.caption("Hisse listesini değiştirmek için `config/tickers.json` dosyasını düzenleyin.")
        st.divider()
        st.markdown("**E-posta Bildirimleri**")
        from services import email_service

        if email_service.is_configured():
            st.success("SMTP yapılandırması tamam.")
        else:
            st.warning("SMTP ayarları eksik — bildirimler devre dışı.")
        st.caption("Ayarlar için Streamlit Secrets veya GitHub Actions Secrets kullanın (bkz. README.md).")
        st.divider()
        st.caption(f"Sayfa yüklenme zamanı: {now_iso()}")


def main() -> None:
    render_sidebar()
    st.title("BIST Finansal Analiz ve Bildirim Uygulaması")
    tab_search, tab_overview, tab_alerts = st.tabs(["🔍 Arama / Detay", "📊 Genel Bakış", "🔔 Bildirim Günlüğü"])

    with tab_search:
        render_search_tab()
    with tab_overview:
        render_overview_tab()
    with tab_alerts:
        render_alert_log_tab()


if __name__ == "__main__":
    main()
