import streamlit as st
import pandas as pd
import re
import requests
from bs4 import BeautifulSoup
import html

# -----------------------------------------------------------------------------
# 1. VISUAL CONFIGURATION (Strict Dejan Style)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Semantic Architect", layout="wide", page_icon="🏛️")

st.markdown("""
<style>
    /* Force Light Mode */
    :root { --primary-color: #1a7f37; --background-color: #ffffff; --secondary-background-color: #f6f8fa; --text-color: #24292e; }
    .stApp { background-color: #ffffff; color: #24292e; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; }
    
    /* Typography */
    h1, h2, h3 { color: #111; font-weight: 600; letter-spacing: -0.5px; }
    
    /* Cards */
    .audit-card {
        border: 1px solid #e1e4e8; border-radius: 8px; padding: 20px; margin-bottom: 15px;
        background: #fff; box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    
    /* Severity Borders */
    .audit-Critical { border-left: 5px solid #d73a49; }
    .audit-High { border-left: 5px solid #d29922; }
    .audit-Medium { border-left: 5px solid #dbab09; }
    .audit-Low { border-left: 5px solid #0969da; }

    /* Badges */
    .badge {
        display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; text-transform: uppercase;
    }
    .bg-Critical { background: #ffebe9; color: #cf222e; }
    .bg-High { background: #fff8c5; color: #9a6700; }
    .bg-Medium { background: #fff8c5; color: #9a6700; }
    .bg-Low { background: #ddf4ff; color: #0969da; }

    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #f6f8fa; border-right: 1px solid #d0d7de; }
    .stTextArea textarea { background-color: #f6f8fa !important; border: 1px solid #d0d7de !important; }
    
    /* Tree View */
    .tree-node { font-family: monospace; padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
    .tree-error { color: #cf222e; font-weight: bold; background: #ffebe9; padding: 2px 5px; border-radius: 4px; }

    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. AUDIT ENGINE
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

def get_snippet(tag):
    """
    Returns a clean, escaped string representation of the opening tag
    plus a hint of its content.
    """
    if not tag: return ""
    
    # Get attributes string: class="foo" id="bar"
    attrs = []
    for k, v in tag.attrs.items():
        val = " ".join(v) if isinstance(v, list) else v
        attrs.append(f'{k}="{val}"')
    attr_str = " ".join(attrs)
    
    if attr_str: attr_str = " " + attr_str
    
    # Opening Tag
    open_tag = f"<{tag.name}{attr_str}>"
    
    # Content Preview (First 50 chars of text)
    text = tag.get_text(" ", strip=True)[:50]
    if text: text += "..."
    
    return f"{open_tag}\n  {text}\n</{tag.name}>"

def audit_logic(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Cleanup scripts for analysis
    for script in soup(["script", "style", "noscript", "svg"]):
        script.decompose()
        
    issues = []
    score_deductions = 0
    
    # --- A. CRITICAL SEO (HEADINGS) ---
    h1s = soup.find_all('h1')
    headings = soup.find_all(re.compile('^h[1-6]$'))
    
    if len(h1s) == 0:
        issues.append({
            "Severity": "Critical",
            "Title": "Missing H1 Tag",
            "Desc": "Search engines rely on the H1 tag to understand the primary topic of the page.",
            "Fix": "Add an <h1> tag containing your target keyword.",
            "Snippet": "<html>",
            "Ref": "Google SEO Starter Guide"
        })
        score_deductions += 25
    elif len(h1s) > 1:
        issues.append({
            "Severity": "High",
            "Title": f"Multiple H1 Tags ({len(h1s)} found)",
            "Desc": "While HTML5 allows this, it dilutes keyword focus. Best practice is one H1 per page.",
            "Fix": "Keep the main title as <h1>, change others to <h2>.",
            "Snippet": get_snippet(h1s[1]), # Show the second H1
            "Ref": "MDN Web Docs"
        })
        score_deductions += 10

    # Heading Hierarchy Check
    if headings:
        prev_level = 0
        for h in headings:
            curr_level = int(h.name[1])
            # Skipping levels (e.g. H2 -> H4) is bad
            if curr_level > prev_level + 1 and prev_level != 0:
                issues.append({
                    "Severity": "Medium",
                    "Title": f"Skipped Heading Level (<h{prev_level}> → <h{curr_level}>)",
                    "Desc": f"The structure jumps directly from H{prev_level} to H{curr_level}, skipping H{prev_level+1}.",
                    "Fix": f"Change this <{h.name}> to <h{prev_level+1}>.",
                    "Snippet": get_snippet(h),
                    "Ref": "WCAG 1.3.1"
                })
                score_deductions += 5
            prev_level = curr_level

    # --- B. STRUCTURAL SEMANTICS (The "Article" Detector) ---
    
    # 1. Detect Main Content Wrapper
    # We look for the container with the highest number of <p> tags
    candidates = []
    for tag in soup.find_all(['div', 'section', 'main', 'article']):
        p_count = len(tag.find_all('p', recursive=False)) # Direct children
        # Also count P tags inside immediate wrappers to be safe
        p_count_deep = len(tag.find_all('p'))
        candidates.append((tag, p_count_deep))
    
    # Sort by paragraph count
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    if candidates:
        top_container, count = candidates[0]
        # If the biggest text container has > 3 paragraphs and isn't <main> or <article>
        if count > 3 and top_container.name not in ['main', 'article']:
            issues.append({
                "Severity": "Critical",
                "Title": "Generic Container for Main Content",
                "Desc": f"The element containing the bulk of your text ({count} paragraphs) is a generic <{top_container.name}>.",
                "Fix": f"Change this <{top_container.name}> to <main> or <article>.",
                "Snippet": get_snippet(top_container),
                "Ref": "HTML5 Specification"
            })
            score_deductions += 15

    # 2. Detect Fake Navigation
    # Look for divs with class "nav", "menu"
    for div in soup.find_all('div'):
        classes = " ".join(div.get('class', [])).lower()
        if 'nav' in classes or 'menu' in classes:
            # Ignore if it's already inside a <nav>
            if not div.find_parent('nav'):
                issues.append({
                    "Severity": "Medium",
                    "Title": "Generic <div> used for Navigation",
                    "Desc": "Found a div with 'nav'/'menu' class but using generic tags.",
                    "Fix": "Change this <div> to <nav>.",
                    "Snippet": get_snippet(div),
                    "Ref": "WAI-ARIA Landmarks"
                })
                score_deductions += 5
                break # Only flag once to avoid spam

    # --- C. ACCESSIBILITY HYGIENE ---
    
    # 1. Alt Text
    images = soup.find_all('img')
    missing_alt = [img for img in images if not img.get('alt')]
    if missing_alt:
        issues.append({
            "Severity": "High",
            "Title": f"{len(missing_alt)} Images Missing Alt Text",
            "Desc": "Images must have a text alternative for screen readers and SEO indexing.",
            "Fix": "Add alt='description' attributes.",
            "Snippet": get_snippet(missing_alt[0]), # Show first offender
            "Ref": "WCAG 1.1.1"
        })
        score_deductions += 10

    # 2. Fake Buttons
    # Anchors with no href or #
    fake_links = soup.find_all('a', href=True)
    bad_links = [a for a in fake_links if a['href'] in ['#', 'javascript:void(0)']]
    if bad_links:
         issues.append({
            "Severity": "Low",
            "Title": "Anchors used as Buttons",
            "Desc": f"Found {len(bad_links)} <a> tags that don't navigate anywhere (href='#' or 'javascript').",
            "Fix": "Use <button> tags for actions that don't change the URL.",
            "Snippet": get_snippet(bad_links[0]),
            "Ref": "MDN: Button vs Anchor"
        })
         score_deductions += 5

    final_score = max(0, 100 - score_deductions)
    return final_score, issues, headings

# -----------------------------------------------------------------------------
# 3. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Config")
    st.markdown("""
    **Logic:** Heuristic DOM Analysis
    <div style="font-size:0.85rem; color:#586069; background:#f6f8fa; padding:10px; border-left:3px solid #1a7f37;">
    <b>How it works:</b>
    This tool performs a structural audit. It identifies the "densest" text block to find your article, checks heading logical order, and detects "fake" semantic elements (divs pretending to be navs).
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 🛡️ Standards")
    st.markdown("""
    *   [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
    *   [WCAG 2.1 Accessibility](https://www.w3.org/TR/WCAG21/)
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

        # --- SECTION 2: VISUAL HIERARCHY ---
        st.markdown("---")
        st.subheader("1. Heading Hierarchy Visualizer")
        st.markdown("This is how Google bots 'read' your content outline. Look for broken indentation.")
        
        if headings_list:
            tree_html = "<div style='background:#fff; padding:15px; border:1px solid #e1e4e8; border-radius:6px; max-height:300px; overflow-y:auto;'>"
            prev_level = 0
            
            for h in headings_list:
                try:
                    lvl = int(h.name[1])
                except:
                    continue # Skip non-standard headings
                
                text = html.escape(h.get_text(strip=True)[:60])
                indent = "&nbsp;" * ((lvl - 1) * 4)
                
                error_marker = ""
                if lvl > prev_level + 1 and prev_level != 0:
                     error_marker = " <span class='tree-error'>[⚠ SKIPPED LEVEL]</span>"
                
                tree_html += f"<div class='tree-node'>{indent}<b>&lt;{h.name}&gt;</b> {text}{error_marker}</div>"
                prev_level = lvl
                
            tree_html += "</div>"
            st.markdown(tree_html, unsafe_allow_html=True)
        else:
            st.warning("No headings (H1-H6) found. This page has no structure.")

        # --- SECTION 3: FORENSIC ISSUES ---
        st.markdown("---")
        st.subheader("2. Forensic Issues & Fixes")
        
        # Sort by severity
        severity_map = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        issues.sort(key=lambda x: severity_map.get(x['Severity'], 4))
        
        if not issues:
            st.info("No issues found.")
        
        for i in issues:
            badge_class = f"bg-{i['Severity']}"
            border_class = f"audit-{i['Severity']}"
            
            # ESCAPE HTML FOR DISPLAY
            safe_snippet = html.escape(i['Snippet'])
            safe_fix = html.escape(i['Fix'])
            
            # But we want to color-code tags in the fix suggestion, so we do a little regex highlighting on the Fix text
            # (Optional polish: convert <tag> to bold)
            display_fix = safe_fix.replace("&lt;", "<b>&lt;").replace("&gt;", "&gt;</b>")

            st.markdown(f"""
            <div class="audit-card {border_class}">
                <div style="margin-bottom:8px;">
                    <span class="badge {badge_class}">{i['Severity']}</span>
                    <span style="font-weight:600; font-size:1.1rem; margin-left:8px;">{i['Title']}</span>
                </div>
                <div style="color:#24292e; margin-bottom:10px;">{i['Desc']}</div>
                
                <!-- Problematic Snippet -->
                <div style="font-size:0.8rem; font-weight:600; color:#586069; margin-bottom:4px;">PROBLMEATIC CODE:</div>
                <pre style="background:#f6f8fa; border:1px solid #d0d7de; padding:8px; border-radius:4px; overflow-x:auto;">{safe_snippet}</pre>
                
                <!-- Fix -->
                <div style="margin-top:10px; font-size:0.9rem;">
                    <span style="font-weight:bold; color:#1a7f37;">⚡ Recommended Fix:</span>
                    <span style="font-family:monospace; background:#e6ffed; padding:2px 6px; border-radius:4px;">{display_fix}</span>
                </div>
                 <div style="font-size:0.75rem; color:#0969da; margin-top:8px; text-align:right;">
                    Standard Reference: {i['Ref']}
                </div>
            </div>
            """, unsafe_allow_html=True)
