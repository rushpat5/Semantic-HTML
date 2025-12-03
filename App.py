import streamlit as st
import pandas as pd
import re
from bs4 import BeautifulSoup
import requests

# -----------------------------------------------------------------------------
# 1. VISUAL CONFIGURATION (Strict Dejan Style)
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
    
    /* Typography */
    h1, h2, h3, h4 {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        font-weight: 600;
        letter-spacing: -0.3px;
        color: #111;
    }
    
    /* Code Snippet Box */
    .snippet-box {
        background-color: #f6f8fa;
        border: 1px solid #d0d7de;
        border-left: 4px solid #cf222e; /* Red error line */
        padding: 10px;
        font-family: 'SFMono-Regular', Consolas, monospace;
        font-size: 0.85rem;
        margin: 5px 0;
        overflow-x: auto;
    }
    
    /* Line Number Badge */
    .line-badge {
        background-color: #24292e;
        color: #fff;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
    }

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
        border-color: #0969da !important;
    }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    [data-testid="stDataFrame"] { border: 1px solid #e1e4e8; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. LOGIC ENGINE (Now with Line Detection)
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

def get_line_number(tag):
    """Returns the line number of a tag if available via lxml."""
    return getattr(tag, 'sourceline', 'Unknown')

def generate_snippet(tag):
    """Converts a tag object back to string for display."""
    return str(tag).split('\n')[0][:150] + "..." # First line only, truncated

def analyze_html(html_content):
    # Use 'lxml' for line number tracking (sourceline)
    try:
        soup = BeautifulSoup(html_content, 'lxml')
    except:
        soup = BeautifulSoup(html_content, 'html.parser') # Fallback
        
    findings = []
    score_deductions = 0
    
    # --- 1. SPECIFIC TAG ANALYSIS ---
    
    # A. Images missing Alt
    images = soup.find_all('img')
    for img in images:
        if not img.get('alt'):
            line = get_line_number(img)
            findings.append({
                "Category": "Accessibility",
                "Severity": "High",
                "Issue": "Image missing alt text",
                "Line": line,
                "Snippet": generate_snippet(img),
                "Fix": 'Add alt="Description of image"'
            })
            score_deductions += 5

    # B. Multiple H1s
    h1s = soup.find_all('h1')
    if len(h1s) > 1:
        for h1 in h1s[1:]: # Skip the first one
            line = get_line_number(h1)
            findings.append({
                "Category": "Headings",
                "Severity": "Medium",
                "Issue": "Duplicate H1 Tag",
                "Line": line,
                "Snippet": generate_snippet(h1),
                "Fix": "Change to <h2> or <div>"
            })
            score_deductions += 5
    elif len(h1s) == 0:
         findings.append({
                "Category": "Headings",
                "Severity": "High",
                "Issue": "No H1 Found",
                "Line": "-",
                "Snippet": "Global",
                "Fix": "Add <h1 >Page Title</h1>"
            })
         score_deductions += 20

    # C. Navigation Divs (Fake Navs)
    # Find divs that look like navs but aren't <nav>
    potential_navs = soup.find_all('div', class_=re.compile(r'nav|menu|header', re.I))
    for div in potential_navs:
        # Heuristic: If it contains list items or links
        if div.find('ul') or len(div.find_all('a')) > 2:
            line = get_line_number(div)
            findings.append({
                "Category": "Structure",
                "Severity": "Medium",
                "Issue": "Generic <div> used for Navigation",
                "Line": line,
                "Snippet": generate_snippet(div),
                "Fix": "Rename <div> to <nav>"
            })
            score_deductions += 5

    # D. Button vs Links
    # Find links with no href or javascript:void
    bad_links = soup.find_all('a', href=re.compile(r'^#$|^javascript:', re.I))
    for a in bad_links:
        line = get_line_number(a)
        findings.append({
            "Category": "Code Quality",
            "Severity": "Low",
            "Issue": "Anchor tag used as Button",
            "Line": line,
            "Snippet": generate_snippet(a),
            "Fix": "Use <button> for actions, <a> for navigation"
        })
        score_deductions += 3

    # --- 2. LANDMARK CHECK ---
    landmarks = ['main', 'header', 'footer']
    for lm in landmarks:
        if not soup.find(lm):
            findings.append({
                "Category": "Structure",
                "Severity": "High",
                "Issue": f"Missing <{lm}> landmark",
                "Line": "Global",
                "Snippet": "-",
                "Fix": f"Wrap content in <{lm}>"
            })
            score_deductions += 10

    # --- 3. HEADING ORDER ---
    headings = soup.find_all(re.compile('^h[1-6]$'))
    if headings:
        current = int(headings[0].name[1])
        if current != 1:
             findings.append({"Category": "Headings", "Severity": "Medium", "Issue": f"Incorrect Start: Page starts with <h{current}>", "Line": get_line_number(headings[0]), "Snippet": generate_snippet(headings[0]), "Fix": "Start with <h1>"})
             score_deductions += 5
             
        for h in headings:
            lvl = int(h.name[1])
            if lvl > current + 1:
                 findings.append({
                    "Category": "Headings",
                    "Severity": "Medium",
                    "Issue": f"Skipped Level (<h{current}> → <h{lvl}>)", 
                    "Line": get_line_number(h), 
                    "Snippet": generate_snippet(h),
                    "Fix": f"Use <h{current+1}>"
                })
            current = lvl

    final_score = max(0, 100 - score_deductions)
    
    # Structure Map
    structure_map = []
    for tag in soup.find_all(['h1', 'h2', 'h3', 'main', 'nav', 'article']):
        indent = 0
        if tag.name.startswith('h'): indent = int(tag.name[1])
        structure_map.append({
            "Tag": tag.name, 
            "Content": tag.get_text(strip=True)[:50], 
            "Indent": indent,
            "Line": get_line_number(tag)
        })

    return final_score, pd.DataFrame(findings), structure_map

# -----------------------------------------------------------------------------
# 3. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Audit Config")
    st.markdown("""
    **Parser:** `lxml` (Line-Aware)
    <div class="tech-note">
    <b>Forensic Mode:</b> This tool locates the exact line number of semantic violations so your dev team can copy-paste fixes.
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
    c1.metric("Semantic Health", f"{score}/100")
    c2.metric("Issues Found", len(findings_df) if not findings_df.empty else 0)
    c3.metric("Structure Nodes", len(structure_map))
    
    # 2. Forensic Findings (The "Exact Code" Part)
    st.subheader("Forensic Findings")
    st.markdown("Specific code blocks requiring remediation.")
    
    if not findings_df.empty:
        for i, row in findings_df.iterrows():
            # Severity Color
            color = "#d73a49" if row['Severity'] == "High" else "#d29922"
            
            with st.expander(f"Line {row['Line']}: {row['Issue']}"):
                col_a, col_b = st.columns([3, 1])
                
                with col_a:
                    st.markdown("**Problematic Code:**")
                    st.markdown(f"""
                    <div class="snippet-box">
                    <span class="line-badge">L{row['Line']}</span> <code>{row['Snippet']}</code>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col_b:
                    st.markdown(f"**Action:**")
                    st.info(row['Fix'])
    else:
        st.success("Clean Code! No semantic errors found.")
        
    # 3. Structure Visualizer
    st.markdown("---")
    st.subheader("Document Outline")
    if structure_map:
        for item in structure_map:
            indent = "&nbsp;" * (item['Indent'] * 4)
            tag_style = "color:#0969da; font-weight:bold;" if item['Tag'] in ['main','nav'] else "color:#24292e;"
            st.markdown(f"<div style='font-family:monospace; font-size:0.9rem;'>{indent}<span style='{tag_style}'>&lt;{item['Tag']}&gt;</span> {item['Content']} <span style='color:#999; font-size:0.7rem;'>(L{item['Line']})</span></div>", unsafe_allow_html=True)
