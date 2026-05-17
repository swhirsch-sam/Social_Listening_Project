import streamlit as st
import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main as analyzer


def sentiment_badge(sentiment):
    colours = {
        'positive': ('#d4edda', '#155724', 'POSITIVE'),
        'negative': ('#f8d7da', '#721c24', 'NEGATIVE'),
        'neutral':  ('#fff3cd', '#856404', 'NEUTRAL'),
    }
    bg, fg, label = colours.get(sentiment, ('#e2e3e5', '#383d41', sentiment.upper()))
    return (
        f'<div style="background:{bg};color:{fg};padding:16px 24px;'
        f'border-radius:10px;font-size:2rem;font-weight:700;'
        f'display:inline-block;margin-bottom:8px">{label}</div>'
    )


def _ui_log_factory(log_lines, log_box):
    def _ui_log(line):
        log_lines.append(line)
        log_box.code('\n'.join(log_lines[-200:]), language='text')
    return _ui_log


def render_results(brand_name, results):
    # --- error guard ---
    if results.get('error'):
        st.error(results['error'])
        return

    # --- pull keys using the names main.py actually returns ---
    overall     = results['dominant']          # was 'overall_sentiment'
    confidence  = results['confidence']
    total       = results['total']             # was 'total_posts'
    counts      = results['counts']            # was 'sentiment_summary'
    pos         = counts.get('positive', 0)
    neu         = counts.get('neutral',  0)
    neg         = counts.get('negative', 0)
    context     = results.get('context', '')
    warnings    = results.get('warnings', [])

    # --- header ---
    if context:
        st.markdown('### Sentiment for **' + brand_name + '** (' + context + ')')
    else:
        st.markdown('### Overall Sentiment for **' + brand_name + '**')

    col_v, col_c, col_t = st.columns([2, 1, 1])
    col_v.markdown(sentiment_badge(overall), unsafe_allow_html=True)
    col_c.metric('Confidence', f'{confidence:.0%}')
    col_t.metric('Posts Analyzed', total)

    if warnings:
        with st.expander('Source warnings'):
            for w in warnings:
                st.warning(w)

    st.divider()

    # --- sentiment breakdown + bar chart ---
    st.markdown('### Sentiment Breakdown')
    c1, c2, c3 = st.columns(3)
    c1.metric('Positive', pos)
    c2.metric('Neutral',  neu)
    c3.metric('Negative', neg)
    chart_df = pd.DataFrame(
        {'Count': [pos, neu, neg]},
        index=['Positive', 'Neutral', 'Negative'],
    )
    st.bar_chart(chart_df, color=['#4a90d9'])
    st.divider()

    # --- top terms ---
    # main.py returns plain word lists e.g. ['great', 'fast', 'quality']
    st.markdown('### Top Mentioned Terms')
    t_pos_col, t_neg_col = st.columns(2)
    pos_terms = results.get('top_positive_terms', [])
    neg_terms = results.get('top_negative_terms', [])

    with t_pos_col:
        st.markdown('**In Positive Posts**')
        if pos_terms:
            for rank, word in enumerate(pos_terms, 1):
                st.markdown(f'{rank}. **{word}**')
        else:
            st.caption('Not enough positive posts.')

    with t_neg_col:
        st.markdown('**In Negative Posts**')
        if neg_terms:
            for rank, word in enumerate(neg_terms, 1):
                st.markdown(f'{rank}. **{word}**')
        else:
            st.caption('Not enough negative posts.')

    st.divider()

    # --- platform breakdown table ---
    st.markdown('### By Platform')
    platform_breakdown = results.get('platform_breakdown', {})
    if platform_breakdown:
        rows = []
        for platform, pdata in platform_breakdown.items():
            rows.append({
                'Platform': platform,
                'Total': pdata['total'],
                'Positive': pdata['positive'],
                'Neutral':  pdata['neutral'],
                'Negative': pdata['negative'],
            })
        plat_df = pd.DataFrame(rows).set_index('Platform')
        st.dataframe(plat_df, use_container_width=True)
    else:
        st.caption('No platform data available.')
    st.divider()

    # --- source coverage strip ---
    st.markdown('### Source Coverage')
    sources = ['TikTok', 'LinkedIn', 'Twitter/X', 'Reddit']
    cov_cols = st.columns(len(sources))
    for i, src in enumerate(sources):
        found = platform_breakdown.get(src, {}).get('total', 0)
        cov_cols[i].metric(src, found if found else '0')
    st.divider()

    # --- individual posts ---
    st.markdown('### Individual Post Breakdown')
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        filter_sentiment = st.selectbox(
            'Filter by sentiment',
            ['All', 'Positive', 'Neutral', 'Negative'],
            key='filter_sentiment',
        )
    with filter_col2:
        all_platforms = sorted({p['platform'] for p in results.get('posts', [])})
        filter_platform = st.selectbox(
            'Filter by platform',
            ['All'] + all_platforms,
            key='filter_platform',
        )

    posts_to_show = list(results.get('posts', []))
    if filter_sentiment != 'All':
        posts_to_show = [p for p in posts_to_show if p['sentiment'] == filter_sentiment.lower()]
    if filter_platform != 'All':
        posts_to_show = [p for p in posts_to_show if p['platform'] == filter_platform]

    st.caption(f'Showing {len(posts_to_show)} of {total} posts')
    for post in posts_to_show:
        senti = post['sentiment']
        label = '[' + post['platform'] + '] ' + (post.get('author') or 'Unknown')
        with st.expander(label):
            st.write(post['content'])
            url = post.get('url', '')
            url_md = f'[View post]({url})' if url else 'No URL'
            st.caption('Sentiment: ' + senti.upper() + ' | ' + url_md)


# ── Header ────────────────────────────────────────────────────────────────
st.title('Brand Sentiment Analyzer')
st.markdown(
    'Enter a brand name to scrape TikTok, LinkedIn, Twitter/X, and Reddit '
    'for recent 2026 mentions and determine overall sentiment.'
)
st.divider()

# ── Input form ────────────────────────────────────────────────────────────
with st.form('brand_form'):
    brand_name = st.text_input(
        label='Brand Name',
        placeholder='e.g. Nike, Airbnb, OpenAI...',
        help='Enter the brand or company name you want to analyze.',
    )
    brand_context = st.text_input(
        label='Context hint (optional)',
        placeholder='e.g. car company, streaming service, sneaker brand...',
        help=(
            'Helps narrow results to the right brand. '
            'For example: Tesla + car company searches for \'Tesla car company\', '
            'filtering out unrelated people or places sharing the name.'
        ),
    )
    submitted = st.form_submit_button('Analyze Sentiment', use_container_width=True)

# ── Run analysis ──────────────────────────────────────────────────────────
if submitted:
    brand_name    = brand_name.strip()
    brand_context = brand_context.strip()
    if not brand_name:
        st.warning('Please enter a brand name before clicking Analyze.')
    else:
        query_display = brand_name + (' + ' + brand_context if brand_context else '')
        log_lines = []
        with st.status(f'Analyzing \'{query_display}\'...', expanded=True) as status:
            log_box      = st.empty()
            progress_bar = st.progress(0, text='Starting...')
            _ui_log      = _ui_log_factory(log_lines, log_box)

            def progress_aware_log(line):
                _ui_log(line)
                if 'Step 1/5' in line:
                    progress_bar.progress(10, text='Step 1/5: Scraping TikTok...')
                elif 'Step 2/5' in line:
                    progress_bar.progress(25, text='Step 2/5: Scraping LinkedIn...')
                elif 'Step 3/5' in line:
                    progress_bar.progress(45, text='Step 3/5: Scraping Twitter/X...')
                elif 'Step 4/5' in line:
                    progress_bar.progress(60, text='Step 4/5: Scraping Reddit...')
                elif 'Step 5/5' in line:
                    progress_bar.progress(78, text='Step 5/5: Conducting sentiment analysis...')

            analyzer.set_log_callback(progress_aware_log)
            results = None
            try:
                results = analyzer.run_analysis(brand_name, brand_context)
                progress_bar.progress(100, text='Complete!')
                status.update(
                    label=f'Done analyzing \'{query_display}\'',
                    state='complete',
                    expanded=False,
                )
            except Exception as exc:
                status.update(label='Analysis failed', state='error', expanded=True)
                st.error(f'Unexpected error: {exc}')
                results = None

        if results is not None:
            render_results(brand_name, results)
