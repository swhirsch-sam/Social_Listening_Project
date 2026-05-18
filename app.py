import streamlit as st
import pandas as pd
import plotly.graph_objects as go
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
    col_c.metric(
        'Confidence',
        f'{confidence:.0%}',
        help=(
            'The percentage of posts that matched the dominant sentiment. '
            'e.g. 72% means 72 out of 100 posts were classified as the dominant sentiment. '
            'A higher score = stronger, more consistent signal.'
        ),
    )
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
    fig = go.Figure(go.Bar(
        x=['Positive', 'Neutral', 'Negative'],
        y=[pos, neu, neg],
        marker_color=['#2ecc71', '#f0ad4e', '#e74c3c'],
        text=[pos, neu, neg],
        textposition='outside',
    ))
    fig.update_layout(
        yaxis_title='Posts',
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(t=20, b=20),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
    )
    st.plotly_chart(fig, use_container_width=True)
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
        all_platforms = sorted({p.get('platform', 'Unknown') for p in results.get('posts', [])})
        filter_platform = st.selectbox(
            'Filter by platform',
            ['All'] + all_platforms,
            key='filter_platform',
        )

    posts_to_show = list(results.get('posts', []))
    if filter_sentiment != 'All':
        posts_to_show = [p for p in posts_to_show if (p.get('sentiment') or '').lower() == filter_sentiment.lower()]
    if filter_platform != 'All':
        posts_to_show = [p for p in posts_to_show if p.get('platform') == filter_platform]

    st.caption(f'Showing {len(posts_to_show)} of {total} posts')
    for post in posts_to_show:
        senti = post.get('sentiment', 'neutral')
        label = '[' + (post.get('platform') or 'Unknown') + '] ' + (post.get('author') or 'Unknown')
        with st.expander(label):
            st.write(post.get('content', ''))
            url = post.get('url', '')
            st.caption('Sentiment: ' + senti.upper())
            if url:
                st.markdown(f'[View post]({url})')


# ── Session state ────────────────────────────────────────────────────────
if 'results' not in st.session_state:
    st.session_state['results'] = None
if 'result_brand' not in st.session_state:
    st.session_state['result_brand'] = ''

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
        progress_bar = st.progress(0)
        with st.status(f'Analyzing \'{query_display}\'...', expanded=True) as status:
            log_box      = st.empty()
            _ui_log      = _ui_log_factory(log_lines, log_box)

            def progress_aware_log(line):
                _ui_log(line)
                if 'Step 1/5' in line:
                    progress_bar.progress(10)
                elif 'Step 2/5' in line:
                    progress_bar.progress(25)
                elif 'Step 3/5' in line:
                    progress_bar.progress(45)
                elif 'Step 4/5' in line:
                    progress_bar.progress(60)
                elif 'Step 5/5' in line:
                    progress_bar.progress(78)

            analyzer.set_log_callback(progress_aware_log)
            try:
                results = analyzer.run_analysis(brand_name, brand_context)
                progress_bar.progress(100)
                status.update(
                    label=f'Done analyzing \'{query_display}\'',
                    state='complete',
                    expanded=False,
                )
                st.session_state['results'] = results
                st.session_state['result_brand'] = brand_name
            except Exception as exc:
                status.update(label='Analysis failed', state='error', expanded=True)
                st.error(f'Unexpected error: {exc}')

# ── Render results (persists across reruns e.g. when filters change) ───────
if st.session_state.get('results') is not None:
    render_results(st.session_state['result_brand'], st.session_state['results'])
