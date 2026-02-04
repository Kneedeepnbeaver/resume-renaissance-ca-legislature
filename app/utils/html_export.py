"""Convert Markdown to styled HTML for PDF export. Uses hardcoded CA Legislature CSS theme."""
from __future__ import annotations

import markdown


# CA Legislature Resume style — Daily File aesthetic adapted for professional resumes
CA_LEGISLATURE_CSS = """
/* CA Legislature Resume — Daily File look, professional resume layout */
.theme-ca-legislature {
    --ink: #000000;
    --paper: #ffffff;
    --muted: #333333;
    --accent: #1a365d;
    --rule: #cccccc;
    --font-body: 'Times New Roman', Times, serif;
    --font-headline: 'Times New Roman', Times, serif;
    background: var(--paper);
    color: var(--ink);
}

.theme-ca-legislature * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

.theme-ca-legislature .theme-content {
    max-width: 8.5in;
    margin: 0 auto;
    padding: 0.6in 0.75in;
    font-family: var(--font-body);
    font-size: 10.5pt;
    line-height: 1.4;
    color: var(--ink);
}

/* Name — larger, prominent (first paragraph) */
.theme-ca-legislature .theme-content > p:first-of-type {
    font-size: 1.65rem;
    font-weight: 700;
    line-height: 1.15;
    margin-bottom: 0.2rem;
}

/* Contact info — not bold (second paragraph) */
.theme-ca-legislature .theme-content > p:nth-of-type(2),
.theme-ca-legislature .theme-content > p:nth-of-type(2) strong {
    font-weight: 400;
    font-size: 10pt;
    margin-bottom: 0.6rem;
}

.theme-ca-legislature h1,
.theme-ca-legislature h2,
.theme-ca-legislature h3,
.theme-ca-legislature h4,
.theme-ca-legislature h5,
.theme-ca-legislature h6 {
    font-family: var(--font-headline);
    font-weight: 700;
    color: var(--ink);
}

.theme-ca-legislature h1 {
    font-size: 1.15rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin: 0.9rem 0 0.4rem;
    padding-bottom: 0.2rem;
    border-bottom: 1px solid var(--ink);
}

.theme-ca-legislature h2 {
    font-size: 1rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    margin: 0.8rem 0 0.35rem;
}

.theme-ca-legislature h3 {
    font-size: 0.95rem;
    margin: 0.6rem 0 0.3rem;
}

.theme-ca-legislature h4,
.theme-ca-legislature h5,
.theme-ca-legislature h6 {
    font-size: 0.9rem;
    margin: 0.5rem 0 0.25rem;
}

.theme-ca-legislature p {
    margin-bottom: 0.5rem;
}

.theme-ca-legislature ul,
.theme-ca-legislature ol {
    margin: 0.35rem 0 0.6rem 1.2rem;
}

.theme-ca-legislature li {
    margin-bottom: 0.25rem;
}

.theme-ca-legislature strong {
    font-weight: 700;
}

.theme-ca-legislature em {
    font-style: italic;
}

.theme-ca-legislature a {
    color: var(--ink);
    text-decoration: none;
}

.theme-ca-legislature a:hover {
    text-decoration: underline;
}

.theme-ca-legislature blockquote {
    border-left: 3px solid var(--ink);
    padding-left: 0.75rem;
    margin: 0.6rem 0;
    color: var(--muted);
}

.theme-ca-legislature hr {
    border: none;
    border-top: 1px solid var(--rule);
    margin: 0.75rem 0;
}

.theme-ca-legislature table {
    width: 100%;
    border-collapse: collapse;
    margin: 0.6rem 0;
    font-size: 9.5pt;
}

.theme-ca-legislature th {
    background: var(--ink);
    color: var(--paper);
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.02em;
    padding: 0.25rem 0.4rem;
    text-align: left;
}

.theme-ca-legislature td {
    padding: 0.2rem 0.4rem;
    border-bottom: 1px solid var(--rule);
}

.theme-ca-legislature tr:nth-child(even) {
    background: #f8f8f8;
}

.theme-ca-legislature code {
    font-family: 'Courier New', monospace;
    font-size: 0.9em;
    background: #f0f0f0;
    padding: 0.05rem 0.2rem;
}

.theme-ca-legislature pre {
    background: #1a1a1a;
    color: #e8e8e8;
    padding: 0.75rem;
    overflow-x: auto;
    margin: 0.6rem 0;
}

.theme-ca-legislature pre code {
    background: transparent;
    border: none;
    padding: 0;
}

/* Print-ready */
@media print {
    .theme-ca-legislature .theme-content {
        padding: 0.5in 0.6in;
        max-width: 100%;
    }
    .theme-ca-legislature {
        background: white;
    }
}
"""


def md_to_html(md_content: str, title: str = "Document") -> str:
    """
    Convert Markdown to a full HTML document with embedded CA Legislature CSS.

    Uses the basic frame from css-themes-styles: theme wrapper + theme-content div.
    Suitable for saving and printing to PDF from browser.
    """
    html_body = markdown.markdown(
        md_content,
        extensions=["tables", "fenced_code", "nl2br"],
        output_format="html5",
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{_escape_html(title)}</title>
    <style>
{CA_LEGISLATURE_CSS}
    </style>
</head>
<body>
    <div class="theme-ca-legislature">
        <div class="theme-content">
{_indent(html_body, 12)}
        </div>
    </div>
</body>
</html>"""


def _escape_html(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _indent(html: str, spaces: int = 4) -> str:
    if not html or not html.strip():
        return ""
    prefix = " " * spaces
    return "\n".join(prefix + line for line in html.strip().splitlines())
