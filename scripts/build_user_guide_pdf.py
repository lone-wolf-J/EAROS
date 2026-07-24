"""Convert /app/USER_GUIDE.md into a distributable, print-quality PDF.

Uses `markdown` for the Markdown→HTML step (with extras for tables + fenced
code + TOC anchors), and WeasyPrint for the HTML→PDF step.
"""
from __future__ import annotations

import re
from pathlib import Path

import markdown
from weasyprint import HTML, CSS

SRC = Path("/app/USER_GUIDE.md")
OUT = Path("/app/EAROS_User_Guide.pdf")

MD_EXTRAS = ["extra", "tables", "fenced_code", "toc", "attr_list", "sane_lists"]

CSS_STR = """
@page {
    size: A4;
    margin: 22mm 18mm 22mm 18mm;
    @bottom-right {
        content: "EAROS User Guide · v2 · Page " counter(page) " of " counter(pages);
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 8pt;
        color: #64748b;
    }
    @bottom-left {
        content: "© Emergent · Confidential";
        font-family: 'Helvetica Neue', Arial, sans-serif;
        font-size: 8pt;
        color: #64748b;
    }
}
@page :first {
    @bottom-right { content: ""; }
    @bottom-left { content: ""; }
}
html { -weasy-hyphens: none; }
body {
    font-family: 'Helvetica Neue', 'Segoe UI', Arial, sans-serif;
    font-size: 10.5pt;
    line-height: 1.55;
    color: #0f172a;
}
.cover {
    page-break-after: always;
    height: 253mm;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: 24mm 14mm 24mm 14mm;
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 65%, #312e81 100%);
    color: #e2e8f0;
    margin: -22mm -18mm 0 -18mm;
    box-sizing: border-box;
    border-radius: 0;
}
.cover .brand {
    font-family: 'Courier New', ui-monospace, monospace;
    font-size: 10pt;
    letter-spacing: 4px;
    color: #a5b4fc;
    text-transform: uppercase;
}
.cover h1 {
    font-size: 42pt;
    font-weight: 900;
    line-height: 1.05;
    letter-spacing: -1px;
    color: #f8fafc;
    margin: 12mm 0 6mm 0;
    border: 0;
}
.cover .subtitle {
    font-size: 15pt;
    color: #cbd5e1;
    font-weight: 300;
    max-width: 130mm;
}
.cover .quote {
    border-left: 3px solid #6366f1;
    padding: 8mm 8mm 8mm 10mm;
    background: rgba(255,255,255,0.04);
    color: #e2e8f0;
    font-size: 11pt;
    line-height: 1.6;
    max-width: 140mm;
}
.cover .meta {
    font-family: 'Courier New', monospace;
    font-size: 9pt;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 2px;
}
h1, h2, h3, h4 {
    font-family: 'Helvetica Neue', 'Segoe UI', Arial, sans-serif;
    color: #0f172a;
    letter-spacing: -0.2px;
}
h1 {
    font-size: 22pt;
    font-weight: 800;
    border-bottom: 2px solid #6366f1;
    padding-bottom: 4mm;
    margin-top: 12mm;
    page-break-before: always;
}
h1:first-of-type { page-break-before: auto; }
h2 {
    font-size: 15pt;
    font-weight: 700;
    color: #4338ca;
    margin-top: 10mm;
    margin-bottom: 3mm;
    border-bottom: 1px solid #e2e8f0;
    padding-bottom: 2mm;
}
h3 {
    font-size: 12.5pt;
    font-weight: 700;
    color: #1e293b;
    margin-top: 7mm;
    margin-bottom: 2mm;
}
h4 {
    font-size: 11pt;
    font-weight: 700;
    color: #334155;
    margin-top: 6mm;
    margin-bottom: 1.5mm;
}
p { margin: 0 0 3mm 0; }
ul, ol { margin: 0 0 4mm 6mm; padding-left: 4mm; }
li { margin-bottom: 1mm; }
strong { color: #0f172a; font-weight: 700; }
em { color: #475569; }
a { color: #4338ca; text-decoration: none; }
blockquote {
    border-left: 3px solid #6366f1;
    background: #f5f3ff;
    padding: 3mm 5mm;
    margin: 4mm 0;
    color: #312e81;
    font-size: 10.5pt;
    border-radius: 0 3px 3px 0;
    page-break-inside: avoid;
}
blockquote strong { color: #4338ca; }
code {
    font-family: 'Courier New', ui-monospace, monospace;
    font-size: 9pt;
    background: #f1f5f9;
    color: #7c2d12;
    padding: 0.5mm 1.4mm;
    border-radius: 2px;
    border: 1px solid #e2e8f0;
}
pre {
    background: #0f172a;
    color: #e2e8f0;
    padding: 4mm;
    border-radius: 3px;
    font-family: 'Courier New', ui-monospace, monospace;
    font-size: 8.5pt;
    line-height: 1.45;
    overflow-x: auto;
    page-break-inside: avoid;
    margin: 4mm 0;
    border: 1px solid #1e293b;
}
pre code { background: transparent; color: inherit; border: 0; padding: 0; }
table {
    width: 100%;
    border-collapse: collapse;
    margin: 4mm 0 6mm 0;
    font-size: 9.5pt;
    page-break-inside: avoid;
}
th {
    background: #1e293b;
    color: #f8fafc;
    text-align: left;
    padding: 2.4mm 3mm;
    font-weight: 700;
    font-size: 9pt;
    letter-spacing: 0.3px;
    border: 1px solid #334155;
}
td {
    padding: 2.2mm 3mm;
    border: 1px solid #e2e8f0;
    vertical-align: top;
}
tbody tr:nth-child(odd) td { background: #f8fafc; }
tbody tr:nth-child(even) td { background: #ffffff; }
hr {
    border: 0;
    border-top: 1px solid #e2e8f0;
    margin: 8mm 0;
}
.pill {
    display: inline-block;
    padding: 0.5mm 2mm;
    border-radius: 999px;
    background: #eef2ff;
    color: #4338ca;
    font-size: 8.5pt;
    font-family: 'Courier New', monospace;
    letter-spacing: 0.5px;
}
h1 + hr, h2 + hr { display: none; }
.footer-brand {
    text-align: center;
    color: #64748b;
    font-family: 'Courier New', monospace;
    font-size: 8.5pt;
    margin-top: 14mm;
    letter-spacing: 2px;
}
"""

COVER_HTML = """
<div class="cover">
  <div>
    <div class="brand">EMERGENT · EAROS</div>
    <h1>Enterprise Autonomous<br/>Recruitment Operating System</h1>
    <div class="subtitle">
      An AI operating system for talent acquisition. Auditable, governed, and
      built to separate intelligence from execution.
    </div>
  </div>
  <div class="quote">
    "Where a traditional ATS asks 'where is this candidate?', EAROS asks 'what
    should we do next?' — and shows the reasoning, one policy-gated step at a
    time."
  </div>
  <div>
    <div class="meta">User Guide · Version 2 · Feb 2026</div>
    <div class="meta" style="margin-top: 2mm; color: #64748b;">
      Interactive Executive Demonstration Build
    </div>
  </div>
</div>
"""


def _clean_markdown(text: str) -> str:
    """Small tweaks so the Markdown renders cleanly in print."""
    # Drop the H1 title from the markdown — we render our own cover page.
    text = re.sub(r"^# EAROS — User Guide\s*\n", "", text, count=1)
    # Drop the "Enterprise Autonomous..." subtitle line and version line that
    # follow the H1 — they are already on the cover.
    text = re.sub(
        r"^\*\*Enterprise Autonomous.*?\*\*\s*\n\s*\n\*Version.*?\*\s*\n",
        "",
        text,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    return text


def build() -> Path:
    md_text = _clean_markdown(SRC.read_text(encoding="utf-8"))
    body_html = markdown.markdown(md_text, extensions=MD_EXTRAS)
    doc = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>EAROS User Guide</title></head>
<body>
{COVER_HTML}
{body_html}
<div class="footer-brand">EAROS · PLANNER → RUNTIME → POLICY → CAPABILITY → GOVERNANCE</div>
</body></html>"""
    HTML(string=doc, base_url=str(SRC.parent)).write_pdf(
        target=str(OUT),
        stylesheets=[CSS(string=CSS_STR)],
    )
    return OUT


if __name__ == "__main__":
    out = build()
    size_kb = out.stat().st_size / 1024
    print(f"Wrote {out} ({size_kb:.1f} KB)")
