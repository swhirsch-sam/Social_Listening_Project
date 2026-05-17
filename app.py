import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main as analyzer

st.set_page_config(
    page_title="Brand Sentiment Analyzer",
    page_icon=":chart_with_upwards_trend:",
    layout="centered",
)

SENTIMENT_COLOR = {"positive": "#2ecc71", "neutral": "#f39c12", "negative": "#e74c3c"}


def sentiment_badge(label):
    color = SENTIMENT_COLOR.get(label, "#888")
    return (
        '<span style="background:' + color + ';color:white;'
        + 'padding:2px 10px;border-radius:12px;font-weight:bold">'
        + label.upper() + "</span>"
    )


def _ui_log_factory(log_lines, log_box):
    def _ui_log(line):
        log_lines.append(line)
        log_box.code("\n".join(log_lines[-200:]), language="text")
    return _ui_log


def render_results(brand_name, results):
    if results.get("error"):
        st.error(results["error"])
        return

    overall = results["overall_sentiment"]
    confidence = results["confidence"]
    total = results["total_posts"]
    summary = results["sentiment_summary"]
    pos = summary.get("positive", 0)
    neu = summary.get("neutral", 0)
    neg = summary.get("negative", 0)

    st.markdown("### Overall Sentiment for **" + brand_name + "**")
    col_v, col_c, col_t = st.columns([2, 1, 1])
    col_v.markdown(sentiment_badge(overall), unsafe_allow_html=True)
    col_c.metric("Confidence", f"{confidence:.0%}")
    col_t.metric("Posts Analyzed", total)

    warnings = results.get("warnings", [])
    if warnings:
        with st.expander("Source warnings"):
            for w in warnings:
                st.warning(w)

    st.divider()

    st.markdown("### Sentiment Breakdown")
    c1, c2, c3 = st.columns(3)
    c1.metric("Positive", pos)
    c2.metric("Neutral", neu)
    c3.metric("Negative", neg)
    chart_df = pd.DataFrame(
        {"Count": [pos, neu, neg]},
        index=["Positive", "Neutral", "Negative"],
    )
    st.bar_chart(chart_df)
    st.divider()

    st.markdown("### Top Mentioned Terms")
    t_pos_col, t_neg_col = st.columns(2)
    pos_terms = results.get("top_positive_terms", [])
    neg_terms = results.get("top_negative_terms", [])
    with t_pos_col:
        st.markdown("**In Positive Posts**")
        if pos_terms:
            for rank, (word, count) in enumerate(pos_terms, 1):
                s = "s" if count != 1 else ""
                st.markdown(f"{rank}. **{word}** - {count} mention{s}")
        else:
            st.caption("Not enough positive posts.")
    with t_neg_col:
        st.markdown("**In Negative Posts**")
        if neg_terms:
            for rank, (word, count) in enumerate(neg_terms, 1):
                s = "s" if count != 1 else ""
                st.markdown(f"{rank}. **{word}** - {count} mention{s}")
        else:
            st.caption("Not enough negative posts.")
    st.divider()

    st.markdown("### By Platform")
    platform_breakdown = results.get("platform_breakdown", {})
    if platform_breakdown:
        rows = []
        for platform, counts in platform_breakdown.items():
            rows.append({
                "Platform": platform,
                "Total": counts["total"],
                "Positive": counts["positive"],
                "Neutral": counts["neutral"],
                "Negative": counts["negative"],
            })
        plat_df = pd.DataFrame(rows).set_index("Platform")
        st.dataframe(plat_df, use_container_width=True)
    else:
        st.caption("No platform data available.")
    st.divider()

    st.markdown("### Source Coverage")
    sources = ["TikTok", "LinkedIn", "Twitter/X", "Reddit", "Instagram"]
    cov_cols = st.columns(len(sources))
    for i, src in enumerate(sources):
        found = platform_breakdown.get(src, {}).get("total", 0)
        cov_cols[i].metric(src, found if found else "0")
    st.divider()

    st.markdown("### Individual Post Breakdown")
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_sentiment = st.selectbox(
            "Filter by sentiment",
            ["All", "Positive", "Neutral", "Negative"],
            key="filter_sentiment",
        )
    with filter_col2:
        all_platforms = sorted({p["platform"] for p in results.get("posts", [])})
        filter_platform = st.selectbox(
            "Filter by platform",
            ["All"] + all_platforms,
            key="filter_platform",
        )

    posts_to_show = results.get("posts", [])
    if filter_sentiment != "All":
        posts_to_show = [
            p for p in posts_to_show if p["sentiment"] == filter_sentiment.lower()
        ]
    if filter_platform != "All":
        posts_to_show = [
            p for p in posts_to_show if p["platform"] == filter_platform
        ]

    st.caption(f"Showing {len(posts_to_show)} of {total} posts")
    for post in posts_to_show:
        senti = post["sentiment"]
        label = "[" + post["platform"] + "] " + (post.get("author") or "Unknown")
        with st.expander(label):
            st.write(post["content"])
            url = post.get("url", "")
            url_md = f"[View post]({url})" if url else "No URL"
            st.caption("Sentiment: " + senti.upper() + " | " + url_md)


# ---------------------------------------------------------------------------
# Main UI
# ---------------------------------------------------------------------------

st.title("Brand Sentiment Analyzer")
st.markdown(
    "Enter a brand name below. The app will scrape TikTok, LinkedIn, "
    "Twitter/X, and Reddit (Instagram temporarily disabled) for recent 2026 mentions "
    "and determine whether overall sentiment is **positive**, **neutral**, or **negative**."
)
st.divider()

with st.form("brand_form"):
    brand_name = st.text_input(
        label="Brand Name",
        placeholder="e.g. Nike, Airbnb, OpenAI...",
        help="Enter the brand or company name you want to analyze.",
    )
    submitted = st.form_submit_button("Analyze Sentiment", use_container_width=True)

if submitted:
    brand_name = brand_name.strip()
    if not brand_name:
        st.warning("Please enter a brand name before clicking Analyze.")
    else:
        status = st.status(
            f"Scraping data for '{brand_name}' and analyzing sentiment...",
            expanded=True,
        )
        log_box = status.empty()
        log_lines = []
        _ui_log = _ui_log_factory(log_lines, log_box)
        analyzer.set_log_callback(_ui_log)
        results = None
        try:
            results = analyzer.run_analysis(brand_name)
            status.update(
                label=f"Done analyzing '{brand_name}'",
                state="complete",
                expanded=False,
            )
        except Exception as e:
            status.update(label=f"Run failed: {e}", state="error", expanded=True)
        finally:
            analyzer.set_log_callback(None)
        if results is not None:
            st.divider()
            render_results(brand_name, results)
