import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup
import requests

# -----------------------------------------------------------------------------
# 1. VISUAL CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Semantic HTML Optimizer", layout="wide", page_icon="🏗️")

st.markdown("""
<style>
    /* --- FORCE LIGHT MODE & TYPOGRAPHY --- */
    :root {
        --primary-color: #1a7f37;
        --background-color: #ffffff;
        --secondary-background-color: #f6f8fa;
        --text-color: #24292e;
        --font: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    }

    .stApp { background-color: #ffffff; color: #24292e; }
    
    h1, h2, h3, h4 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 600;
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
    .metric-val { font-size: 2.2rem; font-weight: 700; margin-bottom: 5px; }
    .metric-label { font-size: 0.85rem; color: #586069; text-transform: uppercase; font-weight: 600; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #f6f8fa; border-right: 1px solid #d0d7de; }
    section[data-testid="stSidebar"] * { color: #24292e !important; }

    /* Inputs */
    .stTextArea textarea, .stTextInput input {
        background-color: #f6f8fa !important;
        border: 1px solid #d0d7de !important;
        color: #24292e !important;
        font-family: 'SFMono-Regular', Consolas, monospace;
    }
    .stTextArea textarea:focus, .stTextInput input:focus {
        border-color: #1a7f37 !important;
    }
    
    /* Buttons */
    div.stButton > button {
        background-color: #1a7f37;
        color: white !important;
        border: none; 
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stDataFrame"] { border: 1px solid #e1e4e8; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOGIC ENGINE
# -----------------------------------------------------------------------------

def fetch_html(url):
    if not url.startswith("http"): url = "https://" + url
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Chrome/120.0.0.0)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.text, None
    except Exception as e:
        return None, str(e)

def get_location_tag(tag, index_map):
    # 1. Try lxml line number
    line = getattr(tag, 'sourceline', None)
    if line: return f"Line {line}"
    
    # 2. Fallback: Nth occurrence
    tag_name = tag.name
    if tag_name not in index_map: index_map[tag_name] = 0
    index_map[tag_name] += 1
    return f"#{index_map[tag_name]}"

def get_raw_html_snippet(tag):
    """
    Robustly reconstructs the opening tag string from attributes.
    This avoids parsing errors where str(tag) returns too much or nothing.
    """
    try:
        # Rebuild the tag manually: <tag class="a" id="b">
        attributes = []
        for key, value in tag.attrs.items():
            # Handle list attributes like class=['btn', 'active']
            if isinstance(value, list):
                value = " ".join(value)
            attributes.append(f'{key}="{value}"')
        
        attr_str = " " + " ".join(attributes) if attributes else ""
        return f"<{tag.name}{attr_str}>"
    except:
        return f"<{tag.name}>"

def analyze_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except:
        soup = BeautifulSoup(html_content, 'html.parser')
        
    findings = []
    score_deductions = 0
    index_map = {} 
    
    # --- 1. IMAGE AUDIT ---
    images = soup.find_all('img')
    for img in images:
        if not img.get('alt'):
            loc = get_location_tag(img, index_map)
            findings.append({
                "Severity": "High",
                "Issue": "Missing Alt Text",
                "Location": loc,
                "Snippet": get_raw_html_snippet(img),
                "Fix": 'Add alt="Description of image"',
                "Why": "Screen readers cannot describe this image."
            })
            score_deductions += 5

    # --- 2. HEADING AUDIT ---
    h1s = soup.find_all('h1')
    if len(h1s) == 0:
        findings.append({
            "Severity": "High",
            "Issue": "Missing H1 Tag",
            "Location": "Global",
            "Snippet": "<html>",
            "Fix": "Add exactly one <h1> containing the main topic.",
            "Why": "H1 is the primary relevance signal."
        })
        score_deductions += 20
    elif len(h1s) > 1:
        for h1 in h1s[1:]:
            loc = get_location_tag(h1, index_map)
            findings.append({
                "Severity": "Medium",
                "Issue": "Multiple H1 Tags",
                "Location": loc,
                "Snippet": get_raw_html_snippet(h1),
                "Fix": "Change to <h2> or <div>.",
                "Why": "Multiple H1s dilute topical focus."
            })
            score_deductions += 5

    # --- 3. DIVITIS DETECTOR ---
    potential_navs = soup.find_all('div', class_=re.compile(r'nav|menu|header', re.I))
    for div in potential_navs:
        if div.find('a'):
            loc = get_location_tag(div, index_map)
            findings.append({
                "Severity": "Medium",
                "Issue": "Generic <div> used for Navigation",
                "Location": loc,
                "Snippet": get_raw_html_snippet(div),
                "Fix": "Rename <div> to <nav>.",
                "Why": "Assistive tech can jump directly to <nav> landmarks."
            })
            score_deductions += 5

    # --- 4. BUTTON CHECK ---
    bad_links = soup.find_all('a')
    for a in bad_links:
        href = a.get('href', '').strip()
        if not href or href.startswith('javascript') or href == '#':
            loc = get_location_tag(a, index_map)
            findings.append({
                "Severity": "Low",
                "Issue": "Anchor <a> used as Button",
                "Location": loc,
                "Snippet": get_raw_html_snippet(a),
                "Fix": "Use <button> for JS actions.",
                "Why": "Anchors are for navigation. Buttons are for actions."
            })
            score_deductions += 2

    # --- 5. LANDMARK CHECK ---
    if not soup.find('main'):
        findings.append({
            "Severity": "High",
            "Issue": "Missing <main> Landmark",
            "Location": "Global",
            "Snippet": "-",
            "Fix": "Wrap unique page content in <main> tags.",
            "Why": "Allows users to 'Skip to Content' immediately."
        })
        score_deductions += 15

    final_score = max(0, 100 - score_deductions)
    
    # Structure Map
    structure_map = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'h4', 'main', 'nav', 'header', 'footer']):
        indent = 0
        # Valid headings check
        if tag.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            indent = int(tag.name[1])
        
        l_num = getattr(tag, 'sourceline', '')
        if l_num: l_num = f"L{l_num}"
        
        structure_map.append({
            "Tag": tag.name, 
            "Content": tag.get_text(" ", strip=True)[:40], 
            "Indent": indent,
            "Line": l_num
        })

    return final_score, pd.DataFrame(findings), structure_map

# -----------------------------------------------------------------------------
# 3. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("""
    **Parser:** `lxml` (Robust)
    <div style="font-size:0.85rem; color:#586069; background:#f6f8fa; padding:12px; border-left:3px solid #1a7f37;">
    <b>Forensic Mode:</b> 
    This engine reconstructs HTML tags so you can identify them in source code even if line numbers are lost.
    </div>
    """, unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 4. MAIN INTERFACE
# -----------------------------------------------------------------------------

st.title("Semantic HTML Optimizer")
st.markdown("### Code-Level Structural Audit")

# --- INPUT ---
tab_url, tab_raw = st.tabs(["🌐 Audit URL", "📝 Paste Source Code"])
html_to_process = None

with tab_url:
    url_input = st.text_input("Target URL", placeholder="https://example.com")
    if st.button("Scan URL", type="primary"):
        if url_input:
            with st.spinner("Fetching & Parsing DOM..."):
                html_data, err = fetch_html(url_input)
                if err: st.error(err)
                else: html_to_process = html_data

with tab_raw:
    raw_input = st.text_area("Raw HTML", height=200)
    if st.button("Scan Code", type="primary"):
        if raw_input: html_to_process = raw_input

# --- OUTPUT ---
if html_to_process:
    score, findings_df, structure_map = analyze_html(html_to_process)
    
    st.markdown("---")
    
    # 1. Scorecard
    c1, c2, c3 = st.columns(3)
    
    def card(col, label, val, color_class):
        col.markdown(f"""
        <div class="metric-container" style="border-top: 4px solid {color_class};">
            <div class="metric-val" style="color: {color_class}">{val}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

    score_color = "#1a7f37" if score > 80 else "#d73a49"
    card(c1, "Semantic Health", f"{score}/100", score_color)
    card(c2, "Issues Found", len(findings_df), "#d29922")
    card(c3, "Structure Nodes", len(structure_map), "#0969da")
    
    # 2. Forensic Findings (THE FIX)
    st.write("")
    st.subheader("Forensic Findings")
    
    if not findings_df.empty:
        for i, row in findings_df.iterrows():
            icon = "🔴" if row['Severity'] == "High" else "🟡"
            label = f"{icon} {row['Issue']} ({row['Location']})"
            
            with st.expander(label):
                col_a, col_b = st.columns([2, 1])
                
                with col_a:
                    st.markdown("**Problematic Code:**")
                    # FIXED: Use st.code() to force display of raw HTML
                    st.code(row['Snippet'], language='html')
                
                with col_b:
                    st.markdown("**Action Required:**")
                    st.info(row['Fix'])
                    st.caption(row['Why'])
    else:
        st.success("Clean Code! No semantic errors found.")
        
    # 3. Structure Visualizer
    st.markdown("---")
    st.subheader("Document Outline")
    if structure_map:
        for item in structure_map:
            indent = "&nbsp;" * (item['Indent'] * 4)
            tag_style = "color:#0969da; font-weight:bold;" if item['Tag'] in ['main','nav'] else "color:#24292e;"
            st.markdown(f"<div style='font-family:monospace; font-size:0.9rem; border-bottom:1px solid #eee; padding:4px;'>{indent}<span style='{tag_style}'>&lt;{item['Tag']}&gt;</span> {item['Content']} <span style='color:#999; font-size:0.7rem; float:right;'>{item['Line']}</span></div>", unsafe_allow_html=True)
