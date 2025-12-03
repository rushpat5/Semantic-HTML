import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup
import requests

# -----------------------------------------------------------------------------
# 1. VISUAL CONFIGURATION (Dejan Style - Light Mode Forced)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Semantic HTML Optimizer", layout="wide", page_icon="🏗️")

st.markdown("""
<style>
    /* --- FORCE LIGHT MODE & ACADEMIC TYPOGRAPHY --- */
    :root {
        --primary-color: #1a7f37; /* GitHub Green */
        --background-color: #ffffff;
        --secondary-background-color: #f6f8fa;
        --text-color: #24292e;
        --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }

    .stApp { background-color: #ffffff; color: #24292e; }
    
    /* Headings */
    h1, h2, h3, h4 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 600;
        letter-spacing: -0.3px;
        color: #111;
    }
    
    /* Metric Cards */
    .metric-container {
        background-color: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .metric-val {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 5px;
    }
    .metric-label {
        font-size: 0.85rem;
        color: #586069;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-weight: 600;
    }
    .good { color: #1a7f37; }
    .warn { color: #d29922; }
    .bad { color: #d73a49; }

    /* Tech Note */
    .tech-note {
        font-size: 0.85rem;
        color: #57606a;
        background-color: #f6f8fa;
        border-left: 3px solid #0969da;
        padding: 12px;
        border-radius: 0 4px 4px 0;
        margin-bottom: 15px;
        line-height: 1.5;
    }

    /* Input Fields */
    .stTextArea textarea, .stTextInput input {
        background-color: #f6f8fa !important;
        border: 1px solid #d0d7de !important;
        color: #24292e !important;
        font-family: 'SFMono-Regular', Consolas, monospace;
        font-size: 0.9rem;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #0969da !important;
        box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.1) !important;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #f6f8fa; border-right: 1px solid #d0d7de; }
    section[data-testid="stSidebar"] * { color: #24292e !important; }

    /* Hide Streamlit Bloat */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stDataFrame"] { border: 1px solid #e1e4e8; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOGIC ENGINE
# -----------------------------------------------------------------------------

def fetch_html(url):
    """Fetches HTML from a URL with a browser User-Agent."""
    if not url.startswith("http"): url = "https://" + url
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text, None
    except Exception as e:
        return None, str(e)

def analyze_html(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    findings = []
    score_deductions = 0
    
    # --- 1. LANDMARK ANALYSIS ---
    landmarks = {
        'main': soup.find('main'),
        'header': soup.find('header'),
        'footer': soup.find('footer'),
        'nav': soup.find('nav'),
        'article': soup.find('article')
    }
    
    if not landmarks['main']:
        findings.append({"Category": "Structure", "Severity": "High", "Issue": "Missing <main> tag", "Fix": "Wrap primary content in <main> for accessibility."})
        score_deductions += 20
    
    if not landmarks['nav']:
        # Check if they used a div class="nav" instead
        nav_class = soup.find('div', class_=re.compile(r'nav|menu', re.I))
        severity = "Medium" if nav_class else "Low"
        findings.append({"Category": "Structure", "Severity": severity, "Issue": "Missing <nav> tag", "Fix": "Wrap menus in <nav> tags."})
        score_deductions += 10

    # --- 2. HEADING HIERARCHY ---
    headings = soup.find_all(re.compile('^h[1-6]$'))
    h1s = soup.find_all('h1')
    
    if len(h1s) == 0:
        findings.append({"Category": "Headings", "Severity": "High", "Issue": "No <h1> found", "Fix": "Define exactly one H1 describing the page entity."})
        score_deductions += 25
    elif len(h1s) > 1:
        findings.append({"Category": "Headings", "Severity": "Medium", "Issue": "Multiple <h1> tags", "Fix": "Use one H1 for the main title; downgrade others to H2."})
        score_deductions += 10
        
    # Check nesting order
    if headings:
        current_level = int(headings[0].name[1])
        if current_level != 1:
             findings.append({"Category": "Headings", "Severity": "Medium", "Issue": "Incorrect Start", "Fix": f"Page starts with <{headings[0].name}>. It should start with <h1>."})
             score_deductions += 5
             
        for h in headings:
            level = int(h.name[1])
            # Skipping levels (e.g., H2 -> H4)
            if level > current_level + 1:
                findings.append({"Category": "Headings", "Severity": "Medium", "Issue": f"Skipped Level (<h{current_level}> → <h{level}>)", "Fix": f"Don't skip levels. Use <h{current_level+1}> instead of <h{level}>."})
                score_deductions += 5
            current_level = level

    # --- 3. DIVITIS (GENERIC VS SEMANTIC) ---
    divs = len(soup.find_all('div'))
    semantics = len(soup.find_all(['section', 'article', 'aside', 'figure', 'figcaption', 'time', 'mark', 'summary', 'details']))
    
    total_containers = divs + semantics
    semantic_ratio = (semantics / total_containers) * 100 if total_containers > 0 else 0
    
    if semantic_ratio < 5 and total_containers > 10:
        findings.append({"Category": "Code Quality", "Severity": "Low", "Issue": "High 'Divitis' detected", "Fix": f"Only {semantic_ratio:.1f}% of containers are semantic. Replace generic <div>s with <section>, <article>, or <aside>."})
        score_deductions += 10

    # --- 4. ACCESSIBILITY / SEO SIGNALS ---
    images = soup.find_all('img')
    missing_alts = [img for img in images if not img.get('alt')]
    if missing_alts:
        findings.append({"Category": "Accessibility", "Severity": "High", "Issue": f"{len(missing_alts)} Images missing alt text", "Fix": "Add descriptive alt text for screen readers and SEO."})
        score_deductions += 15

    # Calculate Score
    final_score = max(0, 100 - score_deductions)
    
    # Structure Map (Fixed Logic)
    structure_map = []
    # Only show headings and major landmarks to keep tree clean
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'main', 'header', 'footer', 'nav', 'article']):
        # Clean text
        text = tag.get_text(strip=True)[:40]
        if len(tag.get_text(strip=True)) > 40: text += "..."
        
        indent = 0
        # FIX: Explicitly check if it's a heading tag before getting indent
        is_heading = tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']
        
        if is_heading:
            indent = int(tag.name[1])
        
        structure_map.append({
            "Tag": f"<{tag.name}>", 
            "Content": text, 
            "Indent": indent,
            "Type": "Heading" if is_heading else "Landmark"
        })

    return final_score, pd.DataFrame(findings), pd.DataFrame(structure_map), semantic_ratio

# -----------------------------------------------------------------------------
# 3. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Audit Config")
    
    st.markdown("""
    **Engine:** BeautifulSoup (HTML Parser)
    <div class="tech-note">
    <b>Definition:</b> Semantic HTML uses elements that carry meaning (e.g., <code>&lt;header&gt;</code>, <code>&lt;article&gt;</code>) rather than generic containers (<code>&lt;div&gt;</code>).
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 📚 References")
    st.markdown("""
    *   [MDN: Semantic HTML](https://developer.mozilla.org/en-US/curriculum/core/semantic-html/)
    *   [Google: SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
    *   [W3C: Accessibility (WAI)](https://www.w3.org/WAI/fundamentals/accessibility-intro/)
    """)

# -----------------------------------------------------------------------------
# 4. MAIN INTERFACE
# -----------------------------------------------------------------------------

st.title("Semantic HTML Optimizer")
st.markdown("### Structural Health & Accessibility Auditor")

with st.expander("Methodology & Nuance (Read First)", expanded=False):
    st.markdown("""
    **The Goal:** Optimize the document structure for machine readability (Bots) and assistive technology (Humans).
    
    **Why it matters:**
    1.  **Accessibility:** Screen readers rely on landmarks (`<nav>`, `<main>`) to navigate.
    2.  **Crawlability:** Google uses headings (`H1-H6`) to understand the hierarchy of importance.
    3.  **Future-Proofing:** Semantic structure is easier for AI agents and Voice Search to interpret than "Div Soup."
    
    *Caveat: Google has stated that semantic HTML is not a magic ranking multiplier, but it is the baseline for a healthy site.*
    """)

st.write("")

# --- INPUT SECTION (TABS) ---
tab_url, tab_raw = st.tabs(["🌐 Audit URL", "📝 Paste HTML Code"])

html_to_process = None

with tab_url:
    url_input = st.text_input("Target URL", placeholder="https://example.com")
    if st.button("Fetch & Audit", type="primary", key="btn_url"):
        if url_input:
            with st.spinner("Fetching source code..."):
                html_data, err = fetch_html(url_input)
                if err:
                    st.error(f"Failed to fetch URL: {err}")
                else:
                    html_to_process = html_data

with tab_raw:
    raw_input = st.text_area("Raw HTML", height=200, placeholder="<html>...</html>")
    if st.button("Audit Code", type="primary", key="btn_raw"):
        if raw_input:
            html_to_process = raw_input

# -----------------------------------------------------------------------------
# 5. RESULTS
# -----------------------------------------------------------------------------

if html_to_process:
    score, findings_df, structure_df, semantic_ratio = analyze_html(html_to_process)
    
    # --- SECTION 1: EXECUTIVE SCORECARD ---
    st.markdown("---")
    st.markdown("### 1. Structural Health")
    
    c1, c2, c3 = st.columns(3)
    
    # Helper for metric color
    def render_metric(col, label, val, unit=""):
        status = "good"
        if isinstance(val, (int, float)):
            if val < 50: status = "bad"
            elif val < 80: status = "warn"
        
        col.markdown(f"""
        <div class="metric-container" style="border-top: 4px solid var(--{status}-color, #586069);">
            <div class="metric-val {status}">{val}{unit}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    render_metric(c1, "Semantic Score", score, "/100")
    render_metric(c2, "Semantic Density", f"{semantic_ratio:.1f}", "%")
    render_metric(c3, "Structure Nodes", len(structure_df))

    # --- SECTION 2: FORENSIC FINDINGS ---
    st.markdown("---")
    st.markdown("### 2. Optimization Opportunities")
    
    if not findings_df.empty:
        # Priority Order: High -> Medium -> Low
        findings_df['Order'] = findings_df['Severity'].map({'High': 0, 'Medium': 1, 'Low': 2})
        findings_df = findings_df.sort_values('Order').drop(columns=['Order'])
        
        for index, row in findings_df.iterrows():
            icon = "🔴" if row['Severity'] == "High" else "🟡" if row['Severity'] == "Medium" else "🔵"
            
            with st.expander(f"{icon} {row['Issue']} ({row['Category']})"):
                st.markdown(f"**Impact:** {row['Fix']}")
                if row['Category'] == "Structure":
                    st.caption("Reference: [MDN Sectioning Elements](https://developer.mozilla.org/en-US/docs/Web/HTML/Element/section)")
                if row['Category'] == "Headings":
                    st.caption("Reference: [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)")
    else:
        st.success("✅ No semantic errors detected. The document structure is clean.")

    # --- SECTION 3: DOCUMENT SKELETON ---
    st.markdown("---")
    st.markdown("### 3. Document Skeleton (Bot View)")
    st.markdown("""<div class="tech-note">This is the hierarchy search engines see. Indentation represents heading depth.</div>""", unsafe_allow_html=True)
    
    if not structure_df.empty:
        # Create a visual tree representation with colors
        def format_row(x):
            indent_str = "&nbsp;&nbsp;&nbsp;&nbsp;" * x['Indent']
            color = "#0969da" if x['Type'] == "Landmark" else "#24292e"
            weight = "700" if x['Type'] == "Landmark" else "400"
            return f"{indent_str}<span style='color:{color}; font-weight:{weight}'>{x['Tag']}</span> <span style='color:#586069'>{x['Content']}</span>"

        structure_df['Visual Hierarchy'] = structure_df.apply(format_row, axis=1)
        
        # Render HTML table
        html_table = structure_df[['Visual Hierarchy']].to_html(escape=False, index=False, header=False, classes="table")
        html_table = html_table.replace('border="1"', 'style="border:1px solid #e1e4e8; width:100%; font-family:monospace; background:#fff;"')
        
        st.markdown(html_table, unsafe_allow_html=True)
    else:
        st.info("No headings or landmarks found.")

    # --- SECTION 4: KNOWLEDGE BASE ---
    st.markdown("---")
    st.markdown("### 4. Implementation Guide")
    
    col_k1, col_k2 = st.columns(2)
    
    with col_k1:
        st.markdown("#### ✅ Do This")
        st.markdown("""
        *   **`<main>`**: Use once per page for the unique content.
        *   **`<article>`**: For self-contained content (blog posts).
        *   **`<nav>`**: For primary navigation menus.
        *   **`<button>` vs `<a>`**: Use Anchors for URLs, Buttons for actions (JS).
        """)
        
    with col_k2:
        st.markdown("#### ❌ Avoid This")
        st.markdown("""
        *   **`<div>` Soup**: Don't use divs for everything.
        *   **Heading Skipping**: Don't jump from `<h1>` to `<h4>` just for styling. Use CSS for size.
        *   **Presentational Tags**: Avoid `<b>` or `<i>` for pure styling; use CSS `font-weight`.
        """)
