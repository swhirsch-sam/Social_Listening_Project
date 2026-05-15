import streamlit as st
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main as analyzer

# Page config
st.set_page_config(
    page_title="Brand Sentiment Analyzer",
    page_icon="chart_with_upwards_trend",
    layout="centered",
)

# Header
st.title("Brand Sentiment Analyzer")
st.markdown(
    "Enter a brand name below. The app will scrape TikTok, LinkedIn, and the web "
    "for **2026 mentions** and determine whether sentiment is "
    "**positive**, **neutral**, or **negative**."
)
st.divider()

# Input form
with st.form("brand_form"):
    brand_name = st.text_input(
        label="Brand Name",
        placeholder="e.g. Nike, Airbnb, OpenAI...",
        help="Enter the brand or company name you want to analyze.",
    )
    submitted = st.form_submit_button("Analyze Sentiment", use_container_width=True)

# Run analysis
if submitted:
    brand_name = brand_name.strip()
    if not brand_name:
        st.warning("Please enter a brand name before clicking Analyze.")
    else:
        with st.spinner(f"Scraping 2026 data for '{brand_name}' and analyzing sentiment..."):
            results = analyzer.run_analysis(brand_name)

        st.divider()

        if results.get("error"):
            st.error(results["error"])
        else:
            sentiment = results["overall_sentiment"]
            confidence = results["confidence"]
            total = results["total_posts"]

            sentiment_icon = {"positive": "GREEN", "neutral": "YELLOW", "negative": "RED"}.get(sentiment, "")
            st.markdown(f"### Overall Sentiment for **{brand_name}**")
            st.markdown(f"## Overall: {sentiment.upper()} ({confidence:.0%} confidence)")
            st.caption(f"Posts analyzed: {total}")
            st.divider()

            # Breakdown metrics
            summary = results["sentiment_summary"]
            col1, col2, col3 = st.columns(3)
            col1.metric("Positive", summary.get("positive", 0))
            col2.metric("Neutral",  summary.get("neutral",  0))
            col3.metric("Negative", summary.get("negative", 0))
            st.divider()

            # Per-source breakdown
            st.subheader("Breakdown by Source")
            sources = {}
            for post in results["posts"]:
                platform = post.get("platform", "Unknown")
                sources.setdefault(platform, {"positive": 0, "neutral": 0, "negative": 0})
                s = post.get("sentiment", "neutral").lower()
                if s in sources[platform]:
                    sources[platform][s] += 1

            for platform, counts in sources.items():
                total_src = sum(counts.values())
                dominant = max(counts, key=counts.get)
                st.markdown(f"**{platform}** ({total_src} posts) — dominant sentiment: *{dominant}*")
                c1, c2, c3 = st.columns(3)
                c1.metric("Positive", counts["positive"])
                c2.metric("Neutral",  counts["neutral"])
                c3.metric("Negative", counts["negative"])

            st.divider()

            # Sample posts
            st.subheader("Sample Posts")
            for post in results["posts"][:10]:
                s = post.get("sentiment", "neutral").lower()
                label = f"[{post['platform']}] {post.get('author','') or 'Unknown'} — {s.capitalize()}"
                with st.expander(label):
                    st.write(post.get("content", "")[:500])
                    if post.get("url"):
                        st.markdown(f"[View original]({post['url']})")
                    st.caption(
                        f"Date: {post.get('date','N/A')}  |  "
                        f"Reason: {post.get('reason','N/A')}  |  "
                        f"Confidence: {post.get('confidence', 0):.0%}"
                    )

st.divider()
st.caption("Data sourced from TikTok (Apify), LinkedIn (Apify), and Web/News (Firecrawl). 2026 content only.")
