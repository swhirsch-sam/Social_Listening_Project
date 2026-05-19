import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main as analyzer

# ── Brand palette ──────────────────────────────────────────────────────────────
BRAND = {
        "primary":    "#6C63FF",   # indigo-violet
        "secondary":  "#F5F3FF",   # lavender tint
        "positive":   "#10B981",   # emerald
        "negative":   "#EF4444",   # rose-red
        "neutral":    "#F59E0B",   # amber
        "bg_card":    "#FFFFFF",
        "text_dark":  "#1F1B4E",
        "text_muted": "#6B7280",
}

# ── Global CSS injection ────────────────────────────────────────────────────────
def inject_global_css():
        st.markdown(
                    f"""
                            <style>
                                    /* ---------- Google Font (Inter) ---------- */
                                            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

                                                    html, body, [class*="css"] {{
                                                                font-family: 'Inter', sans-serif;
                                                                        }}

                                                                                /* ---------- Page background ---------- */
                                                                                        .stApp {{
                                                                                                    background: linear-gradient(135deg, #F5F3FF 0%, #EEF2FF 100%);
                                                                                                            }}
                                                                                                            
                                                                                                                    /* ---------- Sidebar ---------- */
                                                                                                                            [data-testid="stSidebar"] {{
                                                                                                                                        background: {BRAND['text_dark']};
                                                                                                                                                }}
                                                                                                                                                        [data-testid="stSidebar"] * {{
                                                                                                                                                                    color: #E0D9FF !important;
                                                                                                                                                                            }}
                                                                                                                                                                                    [data-testid="stSidebar"] .stTextInput > div > input,
                                                                                                                                                                                            [data-testid="stSidebar"] .stSelectbox > div {{
                                                                                                                                                                                                        background: #2D2760 !important;
                                                                                                                                                                                                                    color: #E0D9FF !important;
                                                                                                                                                                                                                                border: 1px solid #6C63FF !important;
                                                                                                                                                                                                                                            border-radius: 8px !important;
                                                                                                                                                                                                                                                    }}
                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                            /* ---------- Primary button ---------- */
                                                                                                                                                                                                                                                                    .stButton > button {{
                                                                                                                                                                                                                                                                                background: linear-gradient(135deg, {BRAND['primary']}, #8B5CF6) !important;
                                                                                                                                                                                                                                                                                            color: white !important;
                                                                                                                                                                                                                                                                                                        border: none !important;
                                                                                                                                                                                                                                                                                                                    border-radius: 12px !important;
                                                                                                                                                                                                                                                                                                                                font-weight: 600 !important;
                                                                                                                                                                                                                                                                                                                                            font-size: 1rem !important;
                                                                                                                                                                                                                                                                                                                                                        padding: 0.65rem 2rem !important;
                                                                                                                                                                                                                                                                                                                                                                    transition: transform 0.15s, box-shadow 0.15s !important;
                                                                                                                                                                                                                                                                                                                                                                                box-shadow: 0 4px 14px rgba(108,99,255,0.35) !important;
                                                                                                                                                                                                                                                                                                                                                                                        }}
                                                                                                                                                                                                                                                                                                                                                                                                .stButton > button:hover {{
                                                                                                                                                                                                                                                                                                                                                                                                            transform: translateY(-2px) !important;
                                                                                                                                                                                                                                                                                                                                                                                                                        box-shadow: 0 8px 20px rgba(108,99,255,0.45) !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                }}
                                                                                                                                                                                                                                                                                                                                                                                                                                
                                                                                                                                                                                                                                                                                                                                                                                                                                        /* ---------- Metric cards ---------- */
                                                                                                                                                                                                                                                                                                                                                                                                                                                [data-testid="stMetric"] {{
                                                                                                                                                                                                                                                                                                                                                                                                                                                            background: {BRAND['bg_card']};
                                                                                                                                                                                                                                                                                                                                                                                                                                                                        border-radius: 14px;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    padding: 1.1rem 1.4rem;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                box-shadow: 0 2px 12px rgba(108,99,255,0.08);
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            border: 1px solid #E5E1FF;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            [data-testid="stMetricLabel"] {{
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        color: {BRAND['text_muted']} !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    font-size: 0.8rem !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                font-weight: 600 !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            text-transform: uppercase !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        letter-spacing: 0.04em !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        [data-testid="stMetricValue"] {{
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    color: {BRAND['text_dark']} !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                font-size: 2rem !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            font-weight: 800 !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            /* ---------- Expander ---------- */
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    [data-testid="stExpander"] {{
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                background: {BRAND['bg_card']};
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            border: 1px solid #E5E1FF !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        border-radius: 12px !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        /* ---------- DataTable ---------- */
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                [data-testid="stDataFrame"] {{
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            border-radius: 12px;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        overflow: hidden;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    box-shadow: 0 2px 10px rgba(0,0,0,0.06);
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    /* ---------- Headers ---------- */
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            h1 {{ color: {BRAND['text_dark']}; font-weight: 800; letter-spacing: -0.03em; }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    h2 {{ color: {BRAND['text_dark']}; font-weight: 700; }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            h3 {{ color: {BRAND['text_dark']}; font-weight: 600; }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    /* ---------- Divider ---------- */
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            hr {{ border-color: #E5E1FF; }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    /* ---------- Log box ---------- */
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            .stCode, pre {{
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        background: #0F0E1A !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    color: #A5B4FC !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                border-radius: 10px !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            font-family: 'JetBrains Mono', monospace !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        font-size: 0.78rem !important;
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                }}
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        </style>
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                """,
                    unsafe_allow_html=True,
        )


# ── Sentiment badge ─────────────────────────────────────────────────────────────
def sentiment_badge(sentiment):
        styles = {
                    "positive": {
                                    "bg": "linear-gradient(135deg, #D1FAE5, #A7F3D0)",
                                    "color": "#065F46",
                                    "icon": "▲",
                                    "label": "POSITIVE",
                    },
                    "negative": {
                                    "bg": "linear-gradient(135deg, #FEE2E2, #FECACA)",
                                    "color": "#991B1B",
                                    "icon": "▼",
                                    "label": "NEGATIVE",
                    },
                    "neutral": {
                                    "bg": "linear-gradient(135deg, #FEF3C7, #FDE68A)",
                                    "color": "#92400E",
                                    "icon": "●",
                                    "label": "NEUTRAL",
                    },
        }
        s = styles.get(sentiment, {
            "bg": "#F3F4F6", "color": "#374151", "icon": "?", "label": sentiment.upper()
        })
        return (
            f'<div style="background:{s["bg"]};color:{s["color"]};'
            f'padding:18px 28px;border-radius:14px;font-size:1.9rem;font-weight:800;'
            f'display:inline-flex;align-items:center;gap:10px;'
            f'box-shadow:0 2px 12px rgba(0,0,0,0.08);margin-bottom:10px;">'
            f'<span style="font-size:1.4rem">{s["icon"]}</span>{s["label"]}</div>'
        )


# ── Confidence gauge ────────────────────────────────────────────────────────────
def confidence_gauge(confidence: float) -> go.Figure:
        pct = round(confidence * 100)
        color = (
            BRAND["positive"] if pct >= 70
            else BRAND["neutral"] if pct >= 40
            else BRAND["negative"]
        )
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=pct,
            number={"suffix": "%", "font": {"size": 28, "color": BRAND["text_dark"], "family": "Inter"}},
            gauge={
                "axis": {"range": [0, 100], "tickfont": {"size": 11, "color": BRAND["text_muted"]}},
                "bar": {"color": color, "thickness": 0.28},
                "bgcolor": "#F5F3FF",
                "borderwidth": 0,
                "steps": [
                    {"range": [0, 40],  "color": "#FEE2E2"},
                    {"range": [40, 70], "color": "#FEF3C7"},
                    {"range": [70, 100],"color": "#D1FAE5"},
                ],
            },
            domain={"x": [0, 1], "y": [0, 1]},
        ))
        fig.update_layout(
            height=180,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            font={"family": "Inter"},
        )
        return fig


# ── Sentiment donut ─────────────────────────────────────────────────────────────
def sentiment_donut(pos: int, neu: int, neg: int) -> go.Figure:
        fig = go.Figure(go.Pie(
                    labels=["Positive", "Neutral", "Negative"],
                    values=[pos, neu, neg],
                    hole=0.6,
                    marker_colors=[BRAND["positive"], BRAND["neutral"], BRAND["negative"]],
                    textinfo="percent",
                    textfont={"size": 13, "family": "Inter"},
                    hovertemplate="%{label}: %{value} posts<extra></extra>",
        ))
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", y=-0.12, font={"size": 12, "family": "Inter"}),
            margin=dict(l=10, r=10, t=10, b=30),
            height=260,
            paper_bgcolor="rgba(0,0,0,0)",
            font={"family": "Inter"},
        )
        return fig


# ── Platform bar chart ──────────────────────────────────────────────────────────
def platform_bar(platform_counts: dict) -> go.Figure:
        if not platform_counts:
                return None
        platforms = list(platform_counts.keys())
        counts    = list(platform_counts.values())
        colors    = [BRAND["primary"]] * len(platforms)
        fig = go.Figure(go.Bar(
                    x=platforms,
                    y=counts,
                    marker=dict(
                            color=colors,
                            opacity=0.85,
                            line=dict(width=0),
                    ),
                    text=counts,
                    textposition="outside",
                    textfont={"family": "Inter", "size": 12},
                    hovertemplate="%{x}: %{y} posts<extra></extra>",
        ))
        fig.update_layout(
                xaxis=dict(title="", tickfont={"family": "Inter", "size": 12}),
                yaxis=dict(title="Posts", tickfont={"family": "Inter", "size": 12}, gridcolor="#E5E1FF"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=10, b=20),
                height=260,
                font={"family": "Inter"},
                bargap=0.35,
        )
        return fig


# ── Live log helper ─────────────────────────────────────────────────────────────
def _ui_log_factory(log_lines, log_box):
        def _ui_log(line):
                log_lines.append(line)
                log_box.code('\n'.join(log_lines[-200:]), language='text')
        return _ui_log


# ── Results renderer ────────────────────────────────────────────────────────────
def render_results(brand_name: str, results: dict):
        if results.get("error"):
                    st.error(results["error"])
                    return

        overall    = results.get("dominant", "neutral")
        confidence = results.get("confidence", 0.0)
        total      = results.get("total", 0)
        counts     = results.get("counts", {})
        pos        = counts.get("positive", 0)
        neu        = counts.get("neutral",  0)
        neg        = counts.get("negative", 0)
        warnings   = results.get("warnings", [])
        platform_counts = results.get("platform_counts", {})
        posts      = results.get("posts", [])

        # ── Low-volume warning ─────────────────────────────────────────────────────
        if total < 15:
                st.warning(
                                f"⚠️ Only **{total} posts** found for this brand. "
                                "Results may not be representative — interpret with caution.",
                )

        # ── Section heading ────────────────────────────────────────────────────────
        st.markdown(
                f'<h2 style="margin-bottom:4px;">Sentiment Report</h2>'
                f'<p style="color:#6B7280;margin-top:0;font-size:1rem;">Brand: '
                f'<strong style="color:#6C63FF">{brand_name}</strong></p>',
                unsafe_allow_html=True,
        )
        st.divider()

        # ── Top KPI row ────────────────────────────────────────────────────────────
        col_badge, col_conf, col_total, col_pos, col_neg = st.columns([2.5, 2, 1.5, 1.5, 1.5])
        with col_badge:
                st.markdown(sentiment_badge(overall), unsafe_allow_html=True)
        with col_conf:
                st.plotly_chart(confidence_gauge(confidence), use_container_width=True, config={"displayModeBar": False})
        with col_total:
                st.metric("Posts Analysed", total)
        with col_pos:
                pct_pos = round(pos / total * 100) if total else 0
                st.metric("Positive", f"{pct_pos}%", delta=f"{pos} posts", delta_color="normal")
        with col_neg:
                pct_neg = round(neg / total * 100) if total else 0
                st.metric("Negative", f"{pct_neg}%", delta=f"{neg} posts", delta_color="inverse")

        # ── Charts row ─────────────────────────────────────────────────────────────
        col_donut, col_bar = st.columns(2)
        with col_donut:
                st.markdown("##### Sentiment Breakdown")
                st.plotly_chart(sentiment_donut(pos, neu, neg), use_container_width=True, config={"displayModeBar": False})
        with col_bar:
                fig_bar = platform_bar(platform_counts)
                if fig_bar:
                        st.markdown("##### Posts by Platform")
                        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

                    # ── Topic chips ────────────────────────────────────────────────────────────
                    key_topics = results.get("key_topics", [])
        if key_topics:
                st.markdown("##### Top Topics")
                chip_html = " ".join(
                    f'<span style="background:#EEF2FF;color:#4338CA;'
                    f'border-radius:999px;padding:4px 14px;font-size:0.82rem;'
                    f'font-weight:600;margin:3px;display:inline-block;">{t}</span>'
                    for t in key_topics
                )
                st.markdown(chip_html, unsafe_allow_html=True)

        # ── Other warnings ─────────────────────────────────────────────────────────
        for w in warnings:
                st.info(w)

        # ── Posts table ────────────────────────────────────────────────────────────
        if posts:
                st.markdown("---")
                st.markdown("##### Individual Posts")
                df = pd.DataFrame(posts)
                display_cols = [c for c in ["timestamp","platform","author","sentiment","confidence","key_topics","content","url"]
                                if c in df.columns]
                styled = df[display_cols].rename(columns={c: c.replace("_", " ").title() for c in display_cols})

        def _colour_row(row):
                        s = row.get("Sentiment", "").lower() if isinstance(row, dict) else ""
                        bg = {"positive": "#F0FDF4", "negative": "#FFF1F2", "neutral": "#FFFBEB"}.get(s, "")
                        return [f"background-color: {bg}" if bg else "" for _ in row]

        st.dataframe(styled, use_container_width=True, hide_index=True)

        # ── Downloads ──────────────────────────────────────────────────────────
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
                        csv_bytes = df.to_csv(index=False).encode()
                        st.download_button(
                            "⬇ Download CSV",
                            data=csv_bytes,
                            file_name=f"{brand_name}_sentiment.csv",
                            mime="text/csv",
                            use_container_width=True,
                        )
                    with dl_col2:
                                    import json
                                    json_bytes = json.dumps(posts, indent=2, default=str).encode()
                                    st.download_button(
                                        "⬇ Download JSON",
                                        data=json_bytes,
                                        file_name=f"{brand_name}_sentiment.json",
                                        mime="application/json",
                                        use_container_width=True,
                                    )


# ── Main app ────────────────────────────────────────────────────────────────────
def main():
        st.set_page_config(
                    page_title="PulseCheck — Brand Sentiment",
                    page_icon="📡",
                    layout="wide",
                    initial_sidebar_state="expanded",
        )
        inject_global_css()

        # ── Sidebar ───────────────────────────────────────────────────────────────
        with st.sidebar:
                    st.markdown(
                                    '<h1 style="color:#A5B4FC;font-size:1.6rem;font-weight:800;'
                                    'letter-spacing:-0.02em;margin-bottom:2px;">📡 PulseCheck</h1>'
                                    '<p style="color:#7C6FCD;font-size:0.82rem;margin-top:0;">AI-Powered Brand Listening</p>',
                                    unsafe_allow_html=True,
                    )
                    st.markdown("---")

        brand_input = st.text_input(
                        "Brand / Keyword",
                        placeholder="e.g. Nike, Tesla, OpenAI",
                        help="Enter the brand name or keyword you want to analyse.",
        )

        st.markdown("##### 🔌 Data Sources")
        use_tiktok   = st.checkbox("TikTok",   value=True)
        use_linkedin = st.checkbox("LinkedIn",  value=True)
        use_twitter  = st.checkbox("Twitter/X", value=True)
            use_reddit   = st.checkbox("Reddit",    value=True)
        use_web      = st.checkbox("Web / News",value=True)

        st.markdown("---")
        run_btn = st.button("🔍 Run Analysis", use_container_width=True)

        st.markdown(
                        '<p style="color:#6B5EAD;font-size:0.72rem;margin-top:auto;padding-top:2rem;">'
                        'Powered by Claude AI · Apify · Firecrawl</p>',
                        unsafe_allow_html=True,
        )

        # ── Hero / empty state ────────────────────────────────────────────────────
        if not run_btn or not brand_input.strip():
                st.markdown(
                                '<div style="text-align:center;padding:5rem 2rem;">'
                                '<p style="font-size:4rem;margin-bottom:0;">📡</p>'
                                '<h1 style="font-size:2.8rem;font-weight:800;color:#1F1B4E;margin:0.3rem 0;">PulseCheck</h1>'
                                '<p style="font-size:1.15rem;color:#6B7280;max-width:520px;margin:0.5rem auto 2rem;">'
                                'Enter a brand name in the sidebar and click <strong>Run Analysis</strong> '
                                'to get real-time sentiment intelligence from social media &amp; the web.</p>'
                                '<div style="display:inline-flex;gap:12px;flex-wrap:wrap;justify-content:center;">'
                                + "".join(
                                                    f'<span style="background:#EEF2FF;color:#4338CA;border-radius:999px;'
                                                    f'padding:6px 16px;font-size:0.85rem;font-weight:600;">{tag}</span>'
                                                    for tag in ["TikTok", "LinkedIn", "Twitter / X", "Reddit", "Web & News", "AI Summaries"]
                                )
                                + "</div></div>",
                                unsafe_allow_html=True,
                )
                return

        # ── Run analysis ─────────────────────────────────────────────────────────
        brand_name = brand_input.strip()
        st.markdown(f"### Analysing **{brand_name}**…")

        log_lines: list[str] = []
        log_expander = st.expander("📋 Live progress log", expanded=False)
        log_box = log_expander.empty()
        ui_log  = _ui_log_factory(log_lines, log_box)

        source_flags = dict(
                tiktok=use_tiktok,
                linkedin=use_linkedin,
                twitter=use_twitter,
                reddit=use_reddit,
                firecrawl=use_web,
        )

        with st.spinner("Scraping and analysing — this may take a minute…"):
                results = analyzer.run(brand_name, log_fn=ui_log, source_flags=source_flags)

        render_results(brand_name, results)


if __name__ == "__main__":
        main()
