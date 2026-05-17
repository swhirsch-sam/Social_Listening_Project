import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main as analyzer

st.set_page_config(
    page_title="Brand Sentiment Analyzer",
    page_icon=":chart_with_upwards_trend:",
    layout="centered",
)

st.title("Brand Sentiment Analyzer")
st.markdown(
    "Enter a brand name below. The app will scrape TikTok, LinkedIn, Instagram, "
    "Twitter/X, and Reddit for recent mentions and determine whether sentiment is "
    "**positive**, **neutral**, or **negative**."
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
        # Live progress: stream every _log() line from main.py into a status panel
        status = st.status(
            f"Scraping data for '{brand_name}' and analyzing sentiment...",
            expanded=True,
        )
        log_box = status.empty()
        log_lines = []

        def _ui_log(line):
            log_lines.append(line)
            # Render the last ~200 lines as a code block for monospace alignment
            log_box.code("\n".join(log_lines[-200:]), language="text")

        analyzer.set_log_callback(_ui_log)
        try:
            results = analyzer.run_analysis(brand_name)
            status.update(
                label=f"Done analyzing '{brand_name}'",
                state="complete",
                expanded=False,
            )
        except Exception as e:
            status.update(
                label=f"Run failed: {e}",
                state="error",
                expanded=True,
            )
            raise
        finally:
            analyzer.set_log_callback(None)

        st.divider()

        if results.get("error"):
            st.error(results["error"])
        else:
            sentiment = results["overall_sentiment"]
            confidence = results["confidence"]
            total = results["total_posts"]

            st.markdown(f"### Overall Sentiment for **{brand_name}**")
            st.markdown(f"## {sentiment.upper()} ({confidence:.0%} confidence)")
            st.caption(f"Posts analyzed: {total}")

            if results.get("warnings"):
                with st.expander("Source warnings"):
                    for w in results["warnings"]:
                        st.warning(w)

            st.divider()

            summary = results["sentiment_summary"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Positive", summary.get("positive", 0))
            col2.metric("Neutral", summary.get("neutral", 0))
            col3.metric("Negative", summary.get("negative", 0))
            st.divider()

            st.markdown("### Post Breakdown")
            for post in results.get("posts", []):
                with st.expander(f"[{post['platform']}] {post.get('author') or 'Unknown'}"):
                    st.write(post["content"])
                    st.caption(f"Sentiment: **{post['sentiment']}** | URL: {post.get('url', '')}")
