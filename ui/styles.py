"""ui/styles.py: CompilerSense AI design system."""
from __future__ import annotations

import html
from importlib import import_module

st = import_module("streamlit")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500;600;700&display=swap');

:root {
  --bg: #090b10;
  --bg-card: rgba(14, 17, 28, 0.75);
  --border: rgba(124, 58, 237, 0.22);
  --border-subtle: rgba(255, 255, 255, 0.08);

  --accent-purple: #8b5cf6;
  --accent-indigo: #6366f1;
  --accent-cyan: #06b6d4;
  --accent-emerald: #10b981;
  --accent-amber: #f59e0b;
  --accent-rose: #f43f5e;

  --font-sans: 'Inter', system-ui, -apple-system, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

/* Background grid and subtle ambient lighting */
.stApp, [data-testid="stAppViewContainer"] {
  font-family: var(--font-sans) !important;
  color: #e2e8f0 !important;
  background-color: var(--bg) !important;
  background-image: 
    radial-gradient(circle at 50% -10%, rgba(124, 58, 237, 0.22), transparent 50%),
    radial-gradient(circle at 10% 45%, rgba(6, 182, 212, 0.12), transparent 40%),
    radial-gradient(circle at 90% 70%, rgba(139, 92, 246, 0.15), transparent 45%),
    radial-gradient(rgba(255, 255, 255, 0.09) 1px, transparent 1px) !important;
  background-size: 100% 100%, 100% 100%, 100% 100%, 28px 28px !important;
  background-attachment: fixed !important;
}

[data-testid="stHeader"] {
  background: rgba(9, 11, 16, 0.8) !important;
  backdrop-filter: blur(12px) !important;
  border-bottom: 1px solid var(--border-subtle) !important;
}

.block-container {
  padding: 2rem 2.5rem 3.5rem !important;
  max-width: 1380px !important;
}

/* Sidebar */
[data-testid="stSidebar"] {
  background: rgba(11, 14, 23, 0.94) !important;
  backdrop-filter: blur(20px) !important;
  border-right: 1px solid var(--border) !important;
}

[data-testid="stSidebar"] h3 {
  font-family: var(--font-mono) !important;
  font-size: 11px !important;
  letter-spacing: 0.08em !important;
  color: #94a3b8 !important;
  text-transform: uppercase !important;
  margin-top: 10px !important;
  margin-bottom: 6px !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 8px !important;
  background: rgba(14, 17, 28, 0.85) !important;
  padding: 5px 6px !important;
  border-radius: 9999px !important;
  border: 1px solid var(--border) !important;
  backdrop-filter: blur(12px) !important;
  margin-bottom: 22px !important;
  width: fit-content !important;
}

.stTabs [data-baseweb="tab"] {
  height: 38px !important;
  padding: 0 18px !important;
  color: #94a3b8 !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  border-radius: 9999px !important;
  transition: all 0.2s ease !important;
  border: 1px solid transparent !important;
}

.stTabs [data-baseweb="tab"]:hover {
  color: #f8fafc !important;
  background: rgba(255, 255, 255, 0.04) !important;
}

.stTabs [aria-selected="true"] {
  background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%) !important;
  color: #ffffff !important;
  font-weight: 600 !important;
  box-shadow: 0 2px 14px rgba(124, 58, 237, 0.45) !important;
  border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

.stTabs [data-baseweb="tab-highlight"] {
  display: none !important;
}

/* Clean buttons */
.stButton > button {
  border-radius: 9999px !important;
  background: rgba(20, 24, 38, 0.85) !important;
  border: 1px solid rgba(139, 92, 246, 0.35) !important;
  color: #f1f5f9 !important;
  font-weight: 500 !important;
  font-size: 13px !important;
  padding: 0.55rem 1.4rem !important;
  transition: all 0.2s ease !important;
}

.stButton > button:hover {
  border-color: #a855f7 !important;
  color: #ffffff !important;
  background: rgba(30, 36, 56, 0.95) !important;
  box-shadow: 0 0 16px rgba(168, 85, 247, 0.3) !important;
}

.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #7c3aed 0%, #6366f1 100%) !important;
  border: 1px solid rgba(255, 255, 255, 0.28) !important;
  color: #ffffff !important;
  box-shadow: 0 2px 20px rgba(124, 58, 237, 0.5) !important;
  font-weight: 600 !important;
}

.stButton > button[kind="primary"]:hover {
  background: linear-gradient(135deg, #8b5cf6 0%, #4f46e5 100%) !important;
  box-shadow: 0 4px 25px rgba(139, 92, 246, 0.6) !important;
}

/* Glass cards and expanders */
[data-testid="stExpander"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  backdrop-filter: blur(14px) !important;
  margin-bottom: 10px !important;
  overflow: hidden !important;
}

[data-testid="stExpander"]:hover {
  border-color: rgba(139, 92, 246, 0.45) !important;
}

[data-testid="stExpander"] summary {
  color: #f8fafc !important;
  font-weight: 500 !important;
  font-size: 13.5px !important;
  padding: 11px 16px !important;
}

/* Code & Editor */
code, pre, [data-testid="stCode"] * {
  font-family: var(--font-mono) !important;
}

iframe[title*="streamlit_ace"] {
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4) !important;
}

[data-testid="stCode"] {
  background: rgba(10, 13, 22, 0.95) !important;
  border: 1px solid var(--border) !important;
  border-radius: 10px !important;
}

/* Centered hero header */
.cs-hero-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 16px 12px 18px;
  margin: 0 auto 18px;
  max-width: 900px;
}

.cs-hero-pill {
  display: inline-block;
  padding: 5px 14px;
  background: rgba(139, 92, 246, 0.12);
  border: 1px solid rgba(168, 85, 247, 0.35);
  border-radius: 9999px;
  font-size: 11.5px;
  font-weight: 600;
  color: #c084fc;
  margin-bottom: 12px;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  text-align: center;
}

.cs-hero-title {
  text-align: center;
  font-size: 32px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #ffffff;
  margin: 0 0 8px;
  line-height: 1.25;
  background: linear-gradient(180deg, #ffffff 40%, #cbd5e1 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.cs-hero-subtitle {
  text-align: center;
  font-size: 14px;
  color: #94a3b8;
  max-width: 720px;
  margin: 0 auto;
  line-height: 1.55;
  display: block;
}

/* KPI metric cards */
.cs-kpis {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.cs-kpi {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px 16px;
  backdrop-filter: blur(14px);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.25);
  transition: all 0.2s ease;
}

.cs-kpi:hover {
  border-color: rgba(139, 92, 246, 0.5);
  transform: translateY(-1px);
}

.cs-kpi.ok { border-top: 2px solid var(--accent-emerald); }
.cs-kpi.warn { border-top: 2px solid var(--accent-amber); }
.cs-kpi.err { border-top: 2px solid var(--accent-rose); }

.cs-kl {
  font-size: 11px;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #94a3b8;
  font-weight: 600;
  font-family: var(--font-mono);
  margin-bottom: 5px;
}

.cs-kv {
  font: 600 26px var(--font-mono);
  color: #ffffff;
  line-height: 1;
}

/* Diagnostic cards */
.cs-diag {
  background: rgba(13, 16, 26, 0.85);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-left: 3px solid var(--accent-purple);
  border-radius: 8px;
  padding: 10px 14px;
  margin: 6px 0;
  backdrop-filter: blur(10px);
}

.cs-diag.err  { border-left-color: var(--accent-rose); }
.cs-diag.warn { border-left-color: var(--accent-amber); }
.cs-diag.info { border-left-color: var(--accent-cyan); }

.cs-diag .cs-diag-code {
  font-family: var(--font-mono);
  font-size: 11px;
  color: #c084fc;
  margin-bottom: 3px;
}
.cs-diag .cs-diag-msg { color: #f1f5f9; font-weight: 500; font-size: 13px; }
.cs-diag .cs-diag-exp { color: #94a3b8; font-size: 12px; margin-top: 4px; }

/* Status Badges */
.cs-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  border-radius: 9999px;
  font-size: 11px;
  font-weight: 600;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.cs-badge.ok   { background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
.cs-badge.warn { background: rgba(245, 158, 11, 0.12);  color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
.cs-badge.err  { background: rgba(244, 63, 94, 0.12);   color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
.cs-badge.info { background: rgba(6, 182, 212, 0.12);   color: #22d3ee; border: 1px solid rgba(6, 182, 212, 0.3); }
.cs-badge-dot  { width: 5px; height: 5px; border-radius: 50%; background: currentColor; }

/* Sidebar brand */
.cs-brand-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 2px 10px;
}
.cs-brand-mark {
  width: 32px;
  height: 32px;
  background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 13px;
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.2);
  font-family: var(--font-mono);
}
.cs-brand-name {
  font-weight: 700;
  font-size: 15px;
  color: #ffffff;
  letter-spacing: -0.01em;
}
.cs-brand-name span {
  color: #c084fc;
}
.cs-brand-tag {
  font-size: 10px;
  color: #94a3b8;
  font-family: var(--font-mono);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

/* Sidebar statistics */
.cs-sidestat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}
.cs-sidestat-label { font-size: 12px; color: #94a3b8; }
.cs-sidestat-value { font-family: var(--font-mono); font-size: 12px; font-weight: 600; color: #c084fc; }

.cs-ai-on {
  color: #34d399;
  font-weight: 600;
  font-size: 12px;
  font-family: var(--font-mono);
}
.cs-ai-off {
  color: #fbbf24;
  font-weight: 600;
  font-size: 12px;
  font-family: var(--font-mono);
}
</style>
"""

def inject_css() -> None:
    st.markdown(CSS, unsafe_allow_html=True)

def brand() -> None:
    st.markdown(
        '<div class="cs-brand-wrap">'
        '  <div class="cs-brand-mark">CS</div>'
        '  <div>'
        '    <div class="cs-brand-name">Compiler<span>Sense</span> AI</div>'
        '    <div class="cs-brand-tag">C Syntax Analyzer</div>'
        '  </div>'
        '</div>',
        unsafe_allow_html=True,
    )

def hero_banner(title: str, subtitle: str, badge_text: str = "Static Analysis & Auto-Repair") -> None:
    st.markdown(
        f'<div class="cs-hero-wrap" style="text-align:center !important; width:100% !important; margin:0 auto 22px !important; display:flex !important; flex-direction:column !important; align-items:center !important; justify-content:center !important;">'
        f'  <div class="cs-hero-pill" style="margin:0 auto 12px !important; display:inline-block !important; text-align:center !important;">{html.escape(badge_text)}</div>'
        f'  <h1 class="cs-hero-title" style="text-align:center !important; width:100% !important; margin:0 0 10px !important;">{html.escape(title)}</h1>'
        f'  <p class="cs-hero-subtitle" style="text-align:center !important; margin:0 auto !important; width:100% !important; max-width:760px !important; display:block !important;">{html.escape(subtitle)}</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

def page_header(title: str, subtitle: str = "") -> None:
    sub_html = f'<div style="font-size:13px;color:#94a3b8;margin-top:2px;">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(
        f'<div style="margin: 4px 0 16px; padding-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.06);">'
        f'  <h2 style="font-size:18px;font-weight:600;color:#fff;margin:0;letter-spacing:-0.01em;">{html.escape(title)}</h2>'
        f'  {sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )

def badge(text: str, tone: str = "info") -> str:
    return (
        f'<span class="cs-badge {tone}">'
        f'<span class="cs-badge-dot"></span>'
        f'{html.escape(str(text))}'
        f'</span>'
    )

def chip(text: str, tone: str = "") -> str:
    return f'<span class="cs-chip {tone}">{html.escape(str(text))}</span>'

def chips(items: list[tuple[str, str]]) -> None:
    st.markdown(
        '<div style="display:flex;flex-wrap:wrap;gap:6px;margin:6px 0 14px;">'
        + "".join(chip(t, k) for t, k in items) + "</div>",
        unsafe_allow_html=True,
    )

def kpis(items: list[tuple[str, str, str]]) -> None:
    cards = "".join(
        f'<div class="cs-kpi {tone}">'
        f'<div class="cs-kl">{html.escape(label)}</div>'
        f'<div class="cs-kv">{html.escape(value)}</div>'
        f'</div>'
        for label, value, tone in items
    )
    st.markdown(f'<div class="cs-kpis">{cards}</div>', unsafe_allow_html=True)

def diag_card(code: str, location: str, message: str, explanation: str = "", tone: str = "err") -> None:
    exp_html = f'<div class="cs-diag-exp">{html.escape(explanation)}</div>' if explanation else ""
    st.markdown(
        f'<div class="cs-diag {tone}">'
        f'  <div class="cs-diag-code">[{html.escape(code)}] : {html.escape(location)}</div>'
        f'  <div class="cs-diag-msg">{html.escape(message)}</div>'
        f'{exp_html}'
        f'</div>',
        unsafe_allow_html=True,
    )
