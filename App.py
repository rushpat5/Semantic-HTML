import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup, Comment
import html

# -----------------------------------------------------------------------------
# 1. VISUAL CONFIGURATION (Strict Dejan Style)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Semantic Architect", layout="wide", page_icon="🏛️")

st.markdown("""
<style>
    :root { --primary-color: #1a7f37; --background-color: #ffffff; --secondary-background-color: #f6f8fa; --text-color: #24292e; }
    .stApp { background-color: #ffffff; color: #24292e; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
    
    /* Headers */
    h1, h2, h3 { color: #111; font-weight: 600; letter-spacing: -0.5px; }
    
    /* Audit Cards */
    .audit-card {
        border: 1px solid #e1e4e8; border-radius: 8px; padding: 20px; margin-bottom: 15px;
        background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .audit-critical { border-left: 5px solid #d73a49; }
    .audit-warning { border-left: 5px solid #d29922; }
    .audit-info { border-left: 5px solid #0969da; }
    
    /* Badges */
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
    }
    .bg-red { background: #ffebe9; color: #cf222e; }
    .bg-orange { background: #fff8c5; color: #9a6700; }
    .bg-blue { background: #ddf4ff; color: #0969da; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #f6f8fa; border-right: 1px solid #d0d7de; }
    .stTextArea textarea { background-color: #f6f8fa !important; border: 1px solid #d0d7de !important; }
    
    /* Tree View */
    .tree-node { font-family: monospace; padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
    .tree-h1 { font-weight: 700; color: #000; font-size: 1.1rem; }
    .tree-h2 { font-weight: 600; color: #24292e; margin-left: 20px; }
    .tree-h3 { color: #586069; margin-left: 40px; }
    .tree-h4 { color: #6e7781; margin-left: 60px; font-style: italic; }
    .tree-error { color: #cf222e; font-weight: bold; background: #ffebe9; padding: 2px 5px; border-radius: 4px; font-size: 0.8rem; }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. ADVANCED AUDIT ENGINE
# -----------------------------------------------------------------------------

def fetch_source(url):
    if not url.startswith('http'): url = 'https://' + url
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        return r.text, None
    except Exception as e:
        return None, str(e)

def get_tag_preview(tag):
    """Returns the opening tag as a string, truncated."""
    if not tag: return ""
    # Reconstruct attributes
    attrs = []
    for k, v in tag.attrs.items():
        if isinstance(v, list): v = " ".join(v)
        attrs.append(f'{k}="{v}"')
    
    attr_str = " ".join(attrs)
    # Limit length of preview
    if len(attr_str) > 60: attr_str = attr_str[:60] + "..."
    
    return f"<{tag.name} {attr_str}>"

def audit_logic(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove scripts/styles for text analysis
    for script in soup(["script", "style", "noscript"]):
        script.decompose()
        
    issues = []
    score_deductions = 0
    
    # --- A. CRITICAL SEO: HEADING OUTLINE ALGORITHM ---
    headings = soup.find_all(re.compile('^h[1-6]$'))
    h1s = soup.find_all('h1')
    
    if len(h1s) == 0:
        issues.append({
            "Category": "SEO", "Severity": "Critical",
            "Title": "Missing H1 Tag",
            "Desc": "The document has no H1. Search engines use H1 to determine the primary topic.",
            "Fix": "Add a single `<h1>` tag wrapping the page title.",
            "Ref": "Google SEO Starter Guide"
        })
        score_deductions += 25
    elif len(h1s) > 1:
        issues.append({
            "Category": "SEO", "Severity": "High",
            "Title": "Multiple H1 Tags",
            "Desc": f"Found {len(h1s)} H1 tags. While allowed, best practice is one H1 per page.",
            "Fix": "Convert secondary `<h1>` tags to `<h2>`.",
            "Ref": "MDN Web Docs"
        })
        score_deductions += 10

    if headings:
        prev_level = 0
        for h in headings:
            curr_level = int(h.name[1])
            if curr_level > prev_level + 1 and prev_level != 0:
                issues.append({
                    "Category": "SEO", "Severity": "Medium",
                    "Title": f"Broken Heading Hierarchy (<h{prev_level}> → <h{curr_level}>)",
                    "Desc": f"Structure jumps from H{prev_level} directly to H{curr_level}.",
                    "Fix": f"Change `<{h.name}>` to `<h{prev_level+1}>`.",
                    "Ref": "WCAG 1.3.1"
                })
                score_deductions += 5
            prev_level = curr_level

    # --- B. SEMANTIC INFERENCE (Detecting "Fake" Semantics) ---
    semantic_map = {
        "header": ["header", "top-bar", "banner"],
        "nav": ["nav", "menu", "navigation"],
        "footer": ["footer", "bottom", "copyright"],
        "article": ["post", "article", "content-body", "entry"],
        "aside": ["sidebar", "widget", "related"]
    }
    
    divs = soup.find_all('div')
    for div in divs:
        attrs = str(div.get('class', [])) + str(div.get('id', ''))
        attrs = attrs.lower()
        
        for tag_name, keywords in semantic_map.items():
            if any(k in attrs for k in keywords):
                # CRITICAL FIX: Ignore if it's already inside the correct tag
                # e.g. <header><div class="header-inner"> is fine.
                if div.find_parent(tag_name):
                    continue
                
                # Avoid duplicate flags
                if len([x for x in issues if x['Title'] == f"Generic <div> used for {tag_name}"]) < 1:
                    preview = html.escape(get_tag_preview(div))
                    issues.append({
                        "Category": "Semantics", "Severity": "Medium",
                        "Title": f"Generic <div> used for {tag_name}",
                        "Desc": f"Found a `<div>` with class/id identifying it as a **{tag_name}**, but it uses a generic tag.",
                        "Fix": f"Change `{preview}` to `<{tag_name}>`.",
                        "Ref": "MDN Semantic Elements"
                    })
                    score_deductions += 3

    # --- C. LANDMARKS ---
    landmarks = ['main', 'nav', 'header', 'footer']
    for lm in landmarks:
        if not soup.find(lm):
            severity = "Critical" if lm == "main" else "Medium"
            issues.append({
                "Category": "Accessibility", "Severity": severity,
                "Title": f"Missing <{lm}> Landmark",
                "Desc": f"The document lacks a `<{lm}>` region.",
                "Fix": f"Wrap the relevant section in a `<{lm}>` tag.",
                "Ref": "WAI-ARIA Landmarks"
            })
            score_deductions += 10

    # --- D. HYGIENE ---
    images = soup.find_all('img')
    missing_alts = [img for img in images if not img.get('alt')]
    if missing_alts:
        issues.append({
            "Category": "Accessibility", "Severity": "High",
            "Title": f"{len(missing_alts)} Images missing Alt Text",
            "Desc": "Images must have an 'alt' attribute for SEO and Screen Readers.",
            "Fix": "Add `alt='description'` to your `<img>` tags.",
            "Ref": "WCAG 1.1.1"
        })
        score_deductions += 10

    final_score = max(0, 100 - score_deductions)
    
    return final_score, issues, headings

# -----------------------------------------------------------------------------
# 3. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Audit Engine")
    st.markdown("""
    **Logic:** Heuristic DOM Analysis
    <div style="font-size:0.85rem; color:#586069; background:#f6f8fa; padding:10px; border-left:3px solid #1a7f37;">
    <b>How it works:</b>
    This tool parses the HTML Document Object Model (DOM) to verify:
    1. <b>Hierarchy:</b> Are headings logical?
    2. <b>Semantics:</b> Are classes like "nav" using <code>&lt;nav&gt;</code>?
    3. <b>Landmarks:</b> Can bots navigate the regions?
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🛡️ Standards")
    st.markdown("""
    *   [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
    *   [WCAG 2.1 Accessibility](https://www.w3.org/TR/WCAG21/)
    *   [HTML5 Specification](https://html.spec.whatwg.org/multipage/)
    """)

# -----------------------------------------------------------------------------
# 4. MAIN INTERFACE
# -----------------------------------------------------------------------------

st.title("Semantic HTML Architect")
st.markdown("### Structural SEO & Accessibility Audit")

url_input = st.text_input("Enter URL to Audit", placeholder="https://example.com")
run_btn = st.button("Run Structural Audit", type="primary")

if run_btn and url_input:
    
    with st.spinner("Fetching source code & building DOM tree..."):
        html_content, error = fetch_source(url_input)
    
    if error:
        st.error(f"Failed to fetch URL: {error}")
    else:
        score, issues, headings_list = audit_logic(html_content)
        
        # --- SECTION 1: EXECUTIVE SUMMARY ---
        st.markdown("---")
        c1, c2 = st.columns([1, 3])
        
        with c1:
            color = "#1a7f37" if score >= 90 else "#d29922" if score >= 60 else "#d73a49"
            st.markdown(f"""
            <div style="text-align:center; border:2px solid {color}; border-radius:10px; padding:20px;">
                <div style="font-size:3rem; font-weight:bold; color:{color}">{score}</div>
                <div style="font-size:0.8rem; text-transform:uppercase; color:#666;">Semantic Score</div>
            </div>
            """, unsafe_allow_html=True)
            
        with c2:
            st.markdown("### 📊 Audit Summary")
            if score == 100:
                st.success("Perfect Score! Your HTML structure is semantic, accessible, and optimized.")
            else:
                st.markdown(f"We found **{len(issues)} architectural issues**. Prioritize **Critical** errors immediately.")

        # --- SECTION 2: HEADING TREE ---
        st.markdown("---")
        st.subheader("1. Heading Hierarchy Visualizer")
        st.markdown("This is how Google bots 'read' your content outline. Look for broken indentation.")
        
        if headings_list:
            tree_html = "<div style='background:#fff; padding:15px; border:1px solid #e1e4e8; border-radius:6px; max-height:400px; overflow-y:auto;'>"
            prev_level = 0 
            
            for h in headings_list:
                lvl = int(h.name[1])
                # Escape HTML in the text to prevent rendering issues
                text = html.escape(h.get_text(strip=True)[:60])
                
                style_class = f"tree-{h.name}"
                indent = "&nbsp;" * ((lvl - 1) * 4)
                
                error_marker = ""
                if lvl > prev_level + 1 and prev_level != 0:
                     error_marker = " <span class='tree-error'>[⚠ SKIPPED LEVEL]</span>"
                
                tree_html += f"<div class='tree-node'>{indent}<span class='{style_class}'>&lt;{h.name}&gt;</span> {text}{error_marker}</div>"
                prev_level = lvl
                
            tree_html += "</div>"
            st.markdown(tree_html, unsafe_allow_html=True)
        else:
            st.warning("No headings (H1-H6) found. This page has no structure.")

        # --- SECTION 3: FINDINGS ---
        st.markdown("---")
        st.subheader("2. Forensic Issues & Fixes")
        
        severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        issues.sort(key=lambda x: severity_order.get(x['Severity'], 4))
        
        if not issues:
            st.info("No issues found.")
        
        for i in issues:
            border_class = f"audit-{i['Severity'].lower().replace('critical','critical').replace('high','critical').replace('medium','warning')}"
            badge_class = "bg-red" if i['Severity'] in ["Critical", "High"] else "bg-orange" if i['Severity'] == "Medium" else "bg-blue"
            
            st.markdown(f"""
            <div class="audit-card {border_class}">
                <div style="margin-bottom:8px;">
                    <span class="badge {badge_class}">{i['Severity']}</span>
                    <span style="font-weight:600; font-size:1.1rem; margin-left:8px;">{i['Title']}</span>
                </div>
                <div style="color:#24292e; margin-bottom:10px;">{i['Desc']}</div>
                <div style="font-size:0.85rem; color:#57606a; background:#f6f8fa; padding:10px; border-radius:4px;">
                    <strong>⚡ Recommended Fix:</strong> {i['Fix']}
                </div>
                 <div style="font-size:0.75rem; color:#0969da; margin-top:5px; text-align:right;">
                    Standard Reference: {i['Ref']}
                </div>
            </div>
            """, unsafe_allow_html=True)
