import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup, NavigableString
import requests

# -----------------------------------------------------------------------------
# 1. VISUAL CONFIGURATION (Clean Academic Style)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Semantic HTML Architect", layout="wide", page_icon="🏛️")

st.markdown("""
<style>
    :root { --primary-color: #1a7f37; --background-color: #ffffff; --secondary-background-color: #f6f8fa; --text-color: #24292e; --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
    .stApp { background-color: #ffffff; color: #24292e; }
    h1, h2, h3, h4 { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #111; letter-spacing: -0.3px; }
    
    /* Section Headers */
    .category-header {
        font-size: 1.1rem; font-weight: 700; margin-top: 20px; margin-bottom: 10px;
        border-bottom: 2px solid #e1e4e8; padding-bottom: 5px;
    }
    .cat-seo { color: #d73a49; border-color: #d73a49; }
    .cat-structure { color: #d29922; border-color: #d29922; }
    .cat-access { color: #0969da; border-color: #0969da; }

    /* Suggestion Box */
    .suggestion-box {
        background: #ffffff; border: 1px solid #e1e4e8; border-radius: 6px;
        padding: 15px; margin-bottom: 10px; border-left: 4px solid #ccc;
    }
    .suggestion-box.Critical { border-left-color: #d73a49; }
    .suggestion-box.Major { border-left-color: #d29922; }
    .suggestion-box.Minor { border-left-color: #0969da; }
    
    /* Snippet */
    .code-context {
        background: #f6f8fa; padding: 8px; border-radius: 4px;
        font-family: monospace; font-size: 0.85rem; color: #24292e;
        border: 1px solid #d0d7de; margin-top: 8px;
        white-space: pre-wrap;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #f6f8fa; border-right: 1px solid #d0d7de; }
    .stTextArea textarea { background-color: #f6f8fa !important; border: 1px solid #d0d7de !important; }
    div.stButton > button { background-color: #1a7f37; color: white !important; border: none; }
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. INTELLIGENT PARSING ENGINE
# -----------------------------------------------------------------------------

def fetch_html(url):
    if not url.startswith("http"): url = "https://" + url
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Chrome/120.0.0.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        return response.text, None
    except Exception as e:
        return None, str(e)

def get_smart_snippet(tag):
    """
    Generates a snippet that includes the tag AND a preview of its text content
    so the user knows WHICH div this is.
    """
    if not tag: return ""
    
    # 1. Build opening tag with attributes
    attrs = " ".join([f'{k}="{v if isinstance(v, str) else " ".join(v)}"' for k,v in tag.attrs.items()])
    open_tag = f"<{tag.name} {attrs}>" if attrs else f"<{tag.name}>"
    
    # 2. Find first text content (ignoring scripts/styles)
    text_content = ""
    for string in tag.stripped_strings:
        text_content = string
        break # Just get the first piece of text
    
    if len(text_content) > 60: text_content = text_content[:60] + "..."
    
    # 3. Combine
    return f"{open_tag}\n  {text_content}\n..."

def analyze_architecture(html):
    soup = BeautifulSoup(html, 'html.parser')
    report = {
        "SEO": [],        # Critical for rankings (Headings, Title)
        "Structure": [],  # Critical for machine understanding (Landmarks)
        "Quality": []     # Code health (Divitis, Buttons)
    }
    
    # --- A. THE "ARTICLE" HEURISTIC (Intelligent Detection) ---
    # Find the element with the most paragraph text. That IS the article.
    # If it's not an <article> tag, flag it.
    
    content_candidates = []
    for tag in soup.find_all(['div', 'section', 'article', 'main']):
        # Count length of direct text inside p tags
        p_text_len = sum([len(p.get_text()) for p in tag.find_all('p', recursive=False)])
        content_candidates.append((tag, p_text_len))
    
    # Sort by text length
    content_candidates.sort(key=lambda x: x[1], reverse=True)
    
    if content_candidates:
        top_candidate, length = content_candidates[0]
        # Only flag if it has substantial content (e.g. > 500 chars)
        if length > 500:
            if top_candidate.name not in ['article', 'main']:
                report["Structure"].append({
                    "Issue": "Main Content Container is generic",
                    "Severity": "Critical",
                    "Snippet": get_smart_snippet(top_candidate),
                    "Fix": f"Change this <{top_candidate.name}> to an <article> or <main> tag.",
                    "Why": "This element contains the bulk of your text. Wrapping it in <article> tells Google 'This is the blog post/content piece'."
                })
    
    # --- B. HEADING LOGIC ---
    h1s = soup.find_all('h1')
    if not h1s:
        report["SEO"].append({
            "Issue": "Missing H1 Tag",
            "Severity": "Critical",
            "Snippet": "-",
            "Fix": "Add an <h1> tag containing your target keyword/title.",
            "Why": "The H1 is the single most important on-page SEO signal."
        })
    elif len(h1s) > 1:
        report["SEO"].append({
            "Issue": "Multiple H1 Tags found",
            "Severity": "Major",
            "Snippet": get_smart_snippet(h1s[1]),
            "Fix": "Convert secondary H1s to H2.",
            "Why": "Multiple H1s confuse search engines about the primary topic."
        })

    # Check for "Fake Headings" (Divs styled as headings)
    # Look for classes like "h1", "title", "heading" on non-heading tags
    fake_headings = soup.find_all(lambda tag: tag.name not in ['h1','h2','h3','h4','h5','h6'] and tag.get('class') and any(c in ['h1', 'h2', 'title', 'header-text'] for c in tag.get('class')))
    for fake in fake_headings[:3]: # Limit to 3
        report["SEO"].append({
            "Issue": "Semantic Mismatch (Fake Heading)",
            "Severity": "Major",
            "Snippet": get_smart_snippet(fake),
            "Fix": f"Change <{fake.name}> to <h*> tag.",
            "Why": "You are using CSS to make this look like a heading, but Google sees it as plain text."
        })

    # --- C. LANDMARKS & NAVIGATION ---
    if not soup.find('nav'):
        # Look for a div that acts like a nav
        potential_nav = soup.find('div', class_=re.compile('nav|menu', re.I))
        if potential_nav:
             report["Structure"].append({
                "Issue": "Generic <div> used for Menu",
                "Severity": "Major",
                "Snippet": get_smart_snippet(potential_nav),
                "Fix": "Rename <div class='...'> to <nav class='...'>.",
                "Why": "Allows screen readers and bots to jump directly to site navigation."
            })
        else:
            report["Structure"].append({
                "Issue": "No Navigation Landmark",
                "Severity": "Minor",
                "Snippet": "-",
                "Fix": "Wrap your links in a <nav> tag.",
                "Why": "Site structure is unclear to machines."
            })

    # --- D. BUTTON VS LINK ---
    # Finding "Read More" buttons that are actually divs or spans
    fake_buttons = soup.find_all(lambda t: t.name in ['div', 'span'] and t.get('class') and 'btn' in t.get('class') and not t.find('a'))
    for btn in fake_buttons[:2]:
        report["Quality"].append({
            "Issue": "Div used as Button",
            "Severity": "Minor",
            "Snippet": get_smart_snippet(btn),
            "Fix": "Change to <a href='...'> or <button>.",
            "Why": "Non-interactive elements used for interaction break accessibility."
        })

    return report

# -----------------------------------------------------------------------------
# 3. MAIN APP UI
# -----------------------------------------------------------------------------

st.title("Semantic HTML Architect")
st.markdown("### Structure & SEO Validator")

with st.expander("How this tool thinks (Methodology)", expanded=False):
    st.markdown("""
    **Heuristic Analysis:**
    Instead of just checking if tags exist, this tool looks at the **content volume**. 
    
    *   It finds the element with the most text and checks if it's wrapped in an `<article>`.
    *   It finds elements named "menu" and checks if they are `<nav>`.
    *   It finds elements styled like "titles" and checks if they are `<h1>`.
    
    This mimics how a Human SEO Consultant audits code.
    """)

st.write("")

# Input
tab1, tab2 = st.tabs(["🌐 From URL", "📝 From Source Code"])
html_source = None

with tab1:
    url_in = st.text_input("URL", placeholder="https://example.com")
    if st.button("Audit URL"):
        with st.spinner("Fetching DOM..."):
            raw, err = fetch_html(url_in)
            if err: st.error(err)
            else: html_source = raw

with tab2:
    raw_in = st.text_area("HTML Code", height=200)
    if st.button("Audit Code"):
        html_source = raw_in

# Results
if html_source:
    report = analyze_architecture(html_source)
    
    st.markdown("---")
    
    # 1. SEO Critical
    st.markdown(f"<div class='category-header cat-seo'>1. Critical SEO Signals</div>", unsafe_allow_html=True)
    if not report["SEO"]:
        st.success("✅ Headings and Text Signals are optimized.")
    else:
        for item in report["SEO"]:
            st.markdown(f"""
            <div class="suggestion-box {item['Severity']}">
                <strong>{item['Issue']}</strong>
                <div style="margin-top:5px; color:#555;">{item['Fix']}</div>
                <div class="code-context">{item['Snippet']}</div>
                <div style="font-size:0.8rem; color:#777; margin-top:5px;"><em>Why: {item['Why']}</em></div>
            </div>
            """, unsafe_allow_html=True)

    # 2. Structural
    st.markdown(f"<div class='category-header cat-structure'>2. Structural Landmarks (Architecture)</div>", unsafe_allow_html=True)
    if not report["Structure"]:
        st.success("✅ Landmarks (<nav>, <main>, <article>) are correctly defined.")
    else:
        for item in report["Structure"]:
            st.markdown(f"""
            <div class="suggestion-box {item['Severity']}">
                <strong>{item['Issue']}</strong>
                <div style="margin-top:5px; color:#555;">{item['Fix']}</div>
                <div class="code-context">{item['Snippet']}</div>
                <div style="font-size:0.8rem; color:#777; margin-top:5px;"><em>Why: {item['Why']}</em></div>
            </div>
            """, unsafe_allow_html=True)

    # 3. Code Quality
    st.markdown(f"<div class='category-header cat-access'>3. Code Quality & Accessibility</div>", unsafe_allow_html=True)
    if not report["Quality"]:
        st.success("✅ Code semantic quality is high.")
    else:
        for item in report["Quality"]:
            st.markdown(f"""
            <div class="suggestion-box {item['Severity']}">
                <strong>{item['Issue']}</strong>
                <div style="margin-top:5px; color:#555;">{item['Fix']}</div>
                <div class="code-context">{item['Snippet']}</div>
                <div style="font-size:0.8rem; color:#777; margin-top:5px;"><em>Why: {item['Why']}</em></div>
            </div>
            """, unsafe_allow_html=True)
