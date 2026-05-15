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
    "Enter a brand name below. The app will scrape TikTok, LinkedIn, and the web "
    "for recent mentions and determine whether sentiment is "
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
        with st.spinner(f"Scraping data for '{brand_name}' and analyzing sentiment..."):
            results = analyzer.run_analysis(brand_name)

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
