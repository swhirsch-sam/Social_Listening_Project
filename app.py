import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os
import anthropic

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import main as analyze

st.set_page_config(
    page_title="PulseCheck — Brand Sentiment",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
/* GLOBAL */
html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; color: #0d1117; }
.stApp { background-color: #ffffff; }

/* SIDEBAR */
[data-testid="stSidebar"] { background-color: #0a2540; }
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stSidebar"] hr { border-color: #1e4a7a; }
[data-testid="stSidebar"] { display: none; }
[data-testid="collapsedControl"] { display: none; }

/* HEADINGS */
h1, h2, h3, h4 { color: #0a2540; }

/* TEXT INPUT */
div[data-testid="stTextInput"] input {
    background-color: #f0f6ff; color: #0d1117;
        border: 2px solid #1565c0; border-radius: 8px;
            padding: 10px 14px; font-size: 1rem;
            }
            div[data-testid="stTextInput"] input::placeholder { color: #5a85b0; }
            div[data-testid="stTextInput"] input:focus {
                border-color: #1976d2;
                    box-shadow: 0 0 0 3px rgba(21,101,192,0.2);
                        outline: none; background-color: #ffffff;
                        }
                        div[data-testid="stTextInput"] label { color: #0a2540 !important; font-weight: 600; }

                        /* FORM CONTAINER */
                        [data-testid="stForm"] {
                            background-color: #f0f6ff; border: 1px solid #90caf9; border-radius: 12px; padding: 20px;
                            }

                            /* BUTTONS */
                            div[data-testid="stFormSubmitButton"] button, .stButton > button {
                                background-color: #1565c0; color: #ffffff; border: none;
                                    border-radius: 8px; font-weight: 600; font-size: 1rem; padding: 10px 24px;
                                        transition: background-color 0.2s ease;
                                        }
                                        div[data-testid="stFormSubmitButton"] button:hover, .stButton > button:hover {
                                            background-color: #0d47a1; color: #ffffff;
                                            }

                                            /* METRICS */
                                            [data-testid="stMetric"] {
                                                background-color: #e3f2fd; border: 1px solid #90caf9; border-radius: 10px; padding: 14px;
                                                }
                                                [data-testid="stMetricLabel"] { color: #1565c0 !important; font-weight: 600; }
                                                [data-testid="stMetricValue"] { color: #0a2540 !important; }

                                                /* TABS */
                                                .stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #1565c0; gap: 4px; }
                                                .stTabs [data-baseweb="tab"] { color: #5a85b0; background-color: transparent; border-radius: 6px 6px 0 0; font-weight: 500; padding: 8px 18px; }
                                                .stTabs [aria-selected="true"] { color: #ffffff !important; background-color: #1565c0 !important; }

                                                /* EXPANDER */
                                                [data-testid="stExpander"] { border: 1px solid #90caf9; border-radius: 8px; background-color: #f8fbff; }
                                                [data-testid="stExpander"] summary { color: #0a2540; font-weight: 600; }

                                                /* DIVIDER */
                                                hr { border-color: #90caf9; }

                                                /* DATAFRAME */
                                                [data-testid="stDataFrame"] th { background-color: #1565c0 !important; color: #ffffff !important; }
                                                [data-testid="stDataFrame"] td { color: #0d1117; }
                                                </style>
                                                """, unsafe_allow_html=True)
with st.sidebar:
    st.markdown("## 📡 PulseCheck")
    st.caption("Brand Sentiment Intelligence")
    st.divider()



def sentiment_badge(sentiment):
    colours = {
                    'positive': ('#dbeafe', '#1e3a5f', 'POSITIVE'),
                    'negative': ('#0a2540', '#ffffff', 'NEGATIVE'),
                    'neutral':  ('#e8f0fe', '#1565c0', 'NEUTRAL'),
    }
    bg, fg, label = colours.get(sentiment, ('#e2e3e5', '#383d41', sentiment.upper()))
    return (
        f'<div style="background:{bg};color:{fg};padding:16px 24px;'
        f'border-radius:10px;font-size:2rem;font-weight:700;'
        f'display:inline-block;margin-bottom:8px">{label}</div>'
    )


def _ui_log_factory(log_lines, log_box):
    def _ui_log(line):
        log_lines.append(__import__('re').sub(r'^\[\d\d:\d\d:\d\d\] ', '', line))
        log_box.code('\n'.join(log_lines[-200:]), language='text')
    return _ui_log



@st.cache_data(show_spinner=False)
def generate_llm_summary(brand_name, overall, confidence, pos, neu, neg, total, top_pos_terms, top_neg_terms):
    """Call Claude to produce a 2-3 sentence plain-English summary of sentiment results."""
    try:
        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
        pos_pct = round(pos / total * 100) if total else 0
        neg_pct = round(neg / total * 100) if total else 0
        neu_pct = round(neu / total * 100) if total else 0
        pos_terms_str = ', '.join(top_pos_terms[:5]) if top_pos_terms else 'N/A'
        neg_terms_str = ', '.join(top_neg_terms[:5]) if top_neg_terms else 'N/A'
        prompt = (
            f"You are a brand analyst. Summarize these social media sentiment results for \"{brand_name}\" "
            f"in 2-3 concise sentences. Highlight the key takeaway and any notable patterns.\n\n"
            f"Overall sentiment: {overall} (confidence {confidence:.0%})\n"
            f"Breakdown: {pos_pct}% positive, {neu_pct}% neutral, {neg_pct}% negative\n"
            f"Total posts analysed: {total}\n"
            f"Top positive terms: {pos_terms_str}\n"
            f"Top negative terms: {neg_terms_str}"
        )
        msg = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=150,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
    except Exception as e:
        return None

def render_results(brand_name, results):
    # --- error guard ---
    if results.get('error'):
        st.error(results['error'])
        return

    # --- pull keys using the names main.py actually returns ---
    overall     = results.get('dominant', 'neutral')
    confidence  = results.get('confidence', 0.0)
    total       = results.get('total', 0)
    counts      = results.get('counts', {})
    pos         = counts.get('positive', 0)
    neu         = counts.get('neutral',  0)
    neg         = counts.get('negative', 0)
    warnings    = results.get('warnings', [])

    # --- post volume warning ---
    if total < 15:
        st.warning(
            f'⚠️ Only **{total} posts** were found for this brand. '
            'Results may not be representative — treat them with caution.',
        )

    # --- header ---
    st.markdown('### Overall Sentiment for **' + brand_name + '**')

    # --- LLM summary ---
    _summary = generate_llm_summary(
        brand_name, overall, confidence, pos, neu, neg, total,
        results.get('top_positive_terms', []),
        results.get('top_negative_terms', []),
    )
    if _summary:
        st.markdown(
            f'<div style="background:#f0f6ff;border-left:4px solid #1565c0;border-radius:8px;'
            f'padding:14px 18px;margin:12px 0 20px 0;font-size:0.97rem;color:#0a2540;">'
            f'<strong>🤖 AI Summary:</strong> {_summary}</div>',
            unsafe_allow_html=True,
        )

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
    if confidence >= 0.65:
        _sig_bg, _sig_fg, _sig_label, _sig_desc = '#d4edda', '#155724', 'Strong signal', '65%+ of posts align — strong, consistent sentiment.'
    elif confidence >= 0.50:
        _sig_bg, _sig_fg, _sig_label, _sig_desc = '#fff3cd', '#856404', 'Moderate signal', '50–65% agreement — a lean, but some mixed opinions.'
    else:
        _sig_bg, _sig_fg, _sig_label, _sig_desc = '#f8d7da', '#721c24', 'Weak signal', 'Under 50% agreement — mixed or limited data, interpret with caution.'
    col_c.markdown(
        f'<div style="background:{_sig_bg};color:{_sig_fg};padding:4px 8px;'
        f'border-radius:6px;font-size:0.78rem;font-weight:600;text-align:center;margin-top:4px">'
        f'{_sig_label}</div>',
        unsafe_allow_html=True,
    )
    col_c.caption(_sig_desc)
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
    c1.markdown(f'<div style="color:#2ecc71;font-weight:600;font-size:0.85rem">{pos/total:.0%} of posts</div>' if total else '', unsafe_allow_html=True)
    c2.metric('Neutral',  neu)
    c2.markdown(f'<div style="color:#f0ad4e;font-weight:600;font-size:0.85rem">{neu/total:.0%} of posts</div>' if total else '', unsafe_allow_html=True)
    c3.metric('Negative', neg)
    c3.markdown(f'<div style="color:#e74c3c;font-weight:600;font-size:0.85rem">{neg/total:.0%} of posts</div>' if total else '', unsafe_allow_html=True)
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

    # --- highlight cards: most positive & most negative post ---
    _all_scored = results.get('posts', [])
    _pos_posts = [p for p in _all_scored if p.get('sentiment') == 'positive']
    _neg_posts = [p for p in _all_scored if p.get('sentiment') == 'negative']
    if _pos_posts or _neg_posts:
        st.markdown('### Highlights')
        _h_col1, _h_col2 = st.columns(2)
        with _h_col1:
            st.markdown(
                '<div style="background:#f0fff4;border-left:4px solid #2ecc71;'
                'border-radius:8px;padding:14px 16px;min-height:110px">'
                '<div style="font-weight:700;color:#27ae60;margin-bottom:6px">🟢 Most Positive</div>'
                + (
                    '<div style="font-size:0.9rem;color:#0d1117">'
                    + (_pos_posts[0].get('content','')[:280] or '—')
                    + '</div>'
                    '<div style="margin-top:8px;font-size:0.78rem;color:#555">'
                    + _pos_posts[0].get('platform','') + ' · ' + _pos_posts[0].get('author','')
                    + ('  <a href="' + _pos_posts[0].get('url','') + '" target="_blank">View post</a>' if _pos_posts[0].get('url') else '')
                    + '</div>'
                    if _pos_posts else '<div style="color:#555;font-size:0.9rem">No positive posts found.</div>'
                )
                + '</div>',
                unsafe_allow_html=True,
            )
        with _h_col2:
            st.markdown(
                '<div style="background:#fff5f5;border-left:4px solid #e74c3c;'
                'border-radius:8px;padding:14px 16px;min-height:110px">'
                '<div style="font-weight:700;color:#c0392b;margin-bottom:6px">🔴 Most Negative</div>'
                + (
                    '<div style="font-size:0.9rem;color:#0d1117">'
                    + (_neg_posts[0].get('content','')[:280] or '—')
                    + '</div>'
                    '<div style="margin-top:8px;font-size:0.78rem;color:#555">'
                    + _neg_posts[0].get('platform','') + ' · ' + _neg_posts[0].get('author','')
                    + ('  <a href="' + _neg_posts[0].get('url','') + '" target="_blank">View post</a>' if _neg_posts[0].get('url') else '')
                    + '</div>'
                    if _neg_posts else '<div style="color:#555;font-size:0.9rem">No negative posts found.</div>'
                )
                + '</div>',
                unsafe_allow_html=True,
            )

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
                'Total':    pdata.get('total', 0),
                'Positive': pdata.get('positive', 0),
                'Neutral':  pdata.get('neutral', 0),
                'Negative': pdata.get('negative', 0),
            })
        plat_df = pd.DataFrame(rows).set_index('Platform')
        st.dataframe(plat_df, use_container_width=True)
        # grouped bar chart
        _platforms = [r['Platform'] for r in rows]
        _fig_plat = go.Figure(data=[
            go.Bar(name='Positive', x=_platforms, y=[r['Positive'] for r in rows], marker_color='#2ecc71'),
            go.Bar(name='Neutral',  x=_platforms, y=[r['Neutral']  for r in rows], marker_color='#f0ad4e'),
            go.Bar(name='Negative', x=_platforms, y=[r['Negative'] for r in rows], marker_color='#e74c3c'),
        ])
        _fig_plat.update_layout(
            barmode='group',
            yaxis_title='Posts',
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            margin=dict(t=20, b=20),
            yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        )
        st.plotly_chart(_fig_plat, use_container_width=True)
    else:
        st.caption('No platform data available.')
    st.divider()

    # --- source coverage strip ---
    st.markdown('### Source Coverage')
    sources = ['TikTok', 'LinkedIn', 'Twitter/X', 'Reddit', 'YouTube', 'Instagram']
    cov_cols = st.columns(len(sources))
    for i, src in enumerate(sources):
        found = platform_breakdown.get(src, {}).get('total', 0)
        cov_cols[i].metric(src, found if found else '0')
    st.divider()

    # --- export ---------------------------------------------------------------
    st.markdown('### Export Results')
    _export_posts = results.get('posts', [])
    if _export_posts:
        import json as _json
        _exp_col1, _exp_col2 = st.columns(2)
        _csv_df = pd.DataFrame(_export_posts)[['platform', 'author', 'sentiment', 'content', 'url']]
        _exp_col1.download_button(
            label='⬇️ Download posts as CSV',
            data=_csv_df.to_csv(index=False).encode('utf-8'),
            file_name=f'{brand_name.replace(" ", "_")}_sentiment_posts.csv',
            mime='text/csv',
            use_container_width=True,
        )
        _summary = {
            'brand':      brand_name,
            'total':      results.get('total', 0),
            'dominant':   results.get('dominant', ''),
            'confidence': results.get('confidence', 0.0),
            'counts':     results.get('counts', {}),
            'platform_breakdown': results.get('platform_breakdown', {}),
            'top_positive_terms': results.get('top_positive_terms', []),
            'top_negative_terms': results.get('top_negative_terms', []),
        }
        _exp_col2.download_button(
            label='⬇️ Download summary as JSON',
            data=_json.dumps(_summary, indent=2).encode('utf-8'),
            file_name=f'{brand_name.replace(" ", "_")}_sentiment_summary.json',
            mime='application/json',
            use_container_width=True,
        )
    st.divider()

    # --- individual posts (platform tabs) ---
    st.markdown('### Individual Post Breakdown')

    all_posts = list(results.get('posts', []))

    # Sentinel filter: drop posts missing both content and url (malformed entries)
    all_posts = [p for p in all_posts if isinstance(p, dict)]

    # Build platform groups
    platform_names = ['TikTok', 'LinkedIn', 'Twitter/X', 'Reddit', 'YouTube', 'Instagram']
    platform_posts = {pl: [p for p in all_posts if (p.get('platform') or '') == pl]
                      for pl in platform_names}

    # Sentiment filter (applies within the selected platform tab)
    sentiment_filter = st.selectbox(
        'Filter by sentiment',
        ['All', 'Positive', 'Neutral', 'Negative'],
        key='filter_sentiment',
    )

    tab_labels = [f"{pl} ({len(platform_posts[pl])})" for pl in platform_names]
    tabs = st.tabs(tab_labels)

    for tab, pl in zip(tabs, platform_names):
        with tab:
            posts = platform_posts[pl]
            if sentiment_filter != 'All':
                posts = [p for p in posts if (p.get('sentiment') or '').lower() == sentiment_filter.lower()]
            if not posts:
                st.info(f'No {sentiment_filter.lower() if sentiment_filter != "All" else ""} posts found for {pl}.')
            else:
                st.caption(f'Showing {len(posts)} post(s)')
                for post in posts:
                    try:
                        senti  = str(post.get('sentiment') or 'neutral')
                        author = str(post.get('author')    or 'Unknown')
                        plat   = str(post.get('platform')  or pl)
                        content = str(post.get('content')  or '')
                        url    = str(post.get('url')        or '')
                        label  = f'[{plat}] {author}'
                        with st.expander(label):
                            st.write(content)
                            st.caption('Sentiment: ' + senti.upper())
                            if url:
                                st.markdown(f'[View post]({url})')
                    except Exception as e:
                        st.warning(f'Could not render a post: {e}')

# ── Session state ────────────────────────────────────────────────────────
if 'results' not in st.session_state:
    st.session_state['results'] = None
if 'result_brand' not in st.session_state:
    st.session_state['result_brand'] = ''

# ── Header ────────────────────────────────────────────────────────────────
st.title('📡 PulseCheck')
st.caption('Brand Sentiment Intelligence')
st.markdown(
    'Enter a brand name to scrape TikTok, LinkedIn, Twitter/X, Reddit, YouTube, and Instagram '
            'for mentions from the past calendar year and determine overall sentiment.'
)
st.divider()

# ── Input form ────────────────────────────────────────────────────────────
with st.form('brand_form'):
    brand_name = st.text_input(
        label='Brand Name',
        placeholder='e.g. Nike, Airbnb, OpenAI...',
        help='Enter the brand or company name you want to analyze.',
    )
    brand_hint = st.text_input(
        label='Brand Type Hint (optional)',
        placeholder='e.g. automotive manufacturer, coffee chain...',
        help=(
            'Optional: describe what kind of brand this is to help filter out '
            'unrelated posts (e.g. people or places with the same name).'
        ),
    )
    scrape_window = st.radio(
        label='Post date range',
                    options=['In past day', 'In past week', 'In past month', 'In past 3 months', 'In past 6 months', 'In past year'],
                    index=5,
        horizontal=True,
        help='How far back to search for posts across all platforms.',
    )
    # Map display labels to internal keys used by the scrapers
    _window_map = {
                    'In past day':      'day',
                    'In past week':     'week',
                    'In past month':    'month',
                    'In past 3 months': '3months',
                    'In past 6 months': '6months',
                    'In past year':     'year',
    }
    scrape_window_key = _window_map.get(scrape_window, 'year')
    submitted = st.form_submit_button('Analyze Sentiment', use_container_width=True)

# ── Run analysis ──────────────────────────────────────────────────────────
if submitted:
    brand_name    = brand_name.strip()
    brand_hint    = brand_hint.strip()
    if not brand_name:
        st.warning('Please enter a brand name before clicking Analyze.')
    else:
        query_display = brand_name
        log_lines = []
        progress_bar = st.progress(0)
        with st.status(f'Analyzing \'{query_display}\'...', expanded=True) as status:
            log_box      = st.empty()
            _ui_log      = _ui_log_factory(log_lines, log_box)

            def progress_aware_log(line):
                _ui_log(line)
                if 'Step 1/7' in line:
                    progress_bar.progress(10)
                elif 'Step 2/7' in line:
                    progress_bar.progress(25)
                elif 'Step 3/7' in line:
                    progress_bar.progress(45)
                elif 'Step 4/7' in line:
                    progress_bar.progress(60)
                elif 'Step 5/7' in line:
                    progress_bar.progress(64)
                elif 'Step 6/7' in line:
                    progress_bar.progress(78)
                elif 'Step 5/7' in line:
                    progress_bar.progress(78)

            analyze.set_log_callback(progress_aware_log)
            try:
                results = analyze.run_analysis(brand_name, brand_hint, scrape_window=scrape_window_key)
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
