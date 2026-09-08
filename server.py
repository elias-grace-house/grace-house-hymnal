#!/usr/bin/env python3
"""Grace House Hymnal — a tiny local web server for a home church.

Reads plain-text hymns from ./hymns and serves them as a numbered
table of contents plus per-hymn pages, mobile-first, styled to match
the Grace House brand.

The entire site is served under a URL prefix (the "access key") loaded
from ./access-key.txt. Anyone without the key sees a 404 page. The QR
code has the key baked in — one scan = one tap = they're in.

Usage:
    python3 server.py           # serves on port 8000
    python3 server.py 8080      # or pick another port

Add a hymn: drop a file into ./hymns/ named NNN-slug.txt
where NNN is a 3-digit number and slug is any short name.

File format:
    Title of the hymn
    <blank line>
    <optional short label alone on its own line, e.g. "1" or "C">
    Verse line 1
    Verse line 2
    <blank line separates blocks>
    <another optional label>
    More lines
    ...

Labels: any short string (up to 6 chars, no spaces) on its own line
at the start of a block. Examples: 1, 2, 3, C (chorus), B (bridge),
Cd (coda), †. The order of blocks in the file is the order shown.
Repeat a chorus by copy-pasting the C block between verses.
"""
from __future__ import annotations

import http.server
import re
import secrets
import socket
import socketserver
import sys
import urllib.parse
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
HYMNS_DIR = HERE / "hymns"
QR_PATH = HERE / "qr-code.png"
KEY_PATH = HERE / "access-key.txt"
ZINE_PATH = HERE / "zine.txt"
DEFAULT_PORT = 8000

# ─────────────────────────────────────────────────────────────
# Access key

def load_key() -> str:
    if not KEY_PATH.exists():
        key = "grace-" + secrets.token_urlsafe(6).lower().replace("_", "-")
        KEY_PATH.write_text(key + "\n", encoding="utf-8")
    key = KEY_PATH.read_text(encoding="utf-8").strip().split("\n", 1)[0].strip()
    key = re.sub(r"[^A-Za-z0-9_-]", "", key)
    if not key:
        key = "grace-" + secrets.token_urlsafe(6).lower().replace("_", "-")
        KEY_PATH.write_text(key + "\n", encoding="utf-8")
    return key


# ─────────────────────────────────────────────────────────────
# Hymn loading

def load_hymns():
    hymns = []
    for path in HYMNS_DIR.glob("*.txt"):
        m = re.match(r"(\d+)[-_ ](.+)\.txt$", path.name)
        if not m:
            continue
        number = int(m.group(1))
        try:
            with open(path, encoding="utf-8") as f:
                title = f.readline().strip()
        except OSError:
            continue
        if not title:
            title = path.stem
        hymns.append((number, title, path))
    hymns.sort(key=lambda h: h[0])
    return hymns


def parse_zine():
    """Return (title, [(heading, [body_lines]), ...]) from zine.txt,
    or None if the file doesn't exist / is empty.

    Format:
        Title of the page (line 1)

        Section heading
        Body line
        Body line

        Section heading
        - bullet
        - bullet
    """
    if not ZINE_PATH.exists():
        return None
    with open(ZINE_PATH, encoding="utf-8") as f:
        content = f.read()
    lines = content.rstrip().split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    if not lines:
        return None
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    if not body:
        return (title, [])
    raw_sections = re.split(r"\n\s*\n", body)
    sections = []
    for block in raw_sections:
        block_lines = [ln for ln in block.split("\n") if ln.strip() != ""]
        if not block_lines:
            continue
        heading = block_lines[0].strip()
        body_lines = [ln.rstrip() for ln in block_lines[1:]]
        sections.append((heading, body_lines))
    return (title, sections)


def parse_hymn(path):
    """Return (title, [(label, [lines]), ...]).

    A block's first line is treated as its label when it is short
    (<= 6 chars, no spaces) AND there is content after it. Otherwise
    the block is auto-numbered from 1 and its lines are all body.
    """
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = content.rstrip().split("\n")
    if not lines:
        return "", []
    title = lines[0].strip()
    body = "\n".join(lines[1:]).strip()
    if not body:
        return title, []
    raw_blocks = re.split(r"\n\s*\n", body)
    verses = []
    auto_num = 1
    for block in raw_blocks:
        block_lines = [ln.rstrip() for ln in block.split("\n")]
        while block_lines and not block_lines[0].strip():
            block_lines.pop(0)
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()
        if not block_lines:
            continue
        first = block_lines[0].strip()
        is_label = (
            len(first) <= 6
            and " " not in first
            and len(block_lines) > 1
        )
        if is_label:
            label = first
            content_lines = [l for l in block_lines[1:] if l.strip()]
        else:
            label = str(auto_num)
            content_lines = [l for l in block_lines if l.strip()]
            auto_num += 1
        verses.append((label, content_lines))
    return title, verses


# ─────────────────────────────────────────────────────────────
# Templates

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders+Stencil+Display:wght@700;800;900&family=Big+Shoulders+Stencil+Text:wght@500;700;800&family=Special+Elite&display=swap');

* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'Special Elite', 'Courier New', monospace;
  background: #f2ede4;
  color: #0a0a0a;
  -webkit-font-smoothing: antialiased;
  -webkit-text-size-adjust: 100%;
  background-image:
    radial-gradient(circle at 12% 22%, rgba(0,0,0,0.5) 0.5px, transparent 1.5px),
    radial-gradient(circle at 34% 66%, rgba(0,0,0,0.4) 0.5px, transparent 1.5px),
    radial-gradient(circle at 68% 12%, rgba(0,0,0,0.45) 0.5px, transparent 1.4px),
    radial-gradient(circle at 84% 78%, rgba(0,0,0,0.35) 0.4px, transparent 1.3px),
    radial-gradient(circle at 52% 40%, rgba(0,0,0,0.3) 0.4px, transparent 1.2px),
    radial-gradient(circle at 8% 88%, rgba(0,0,0,0.4) 0.5px, transparent 1.4px),
    radial-gradient(circle at 92% 34%, rgba(0,0,0,0.3) 0.4px, transparent 1.2px),
    radial-gradient(circle at 44% 82%, rgba(0,0,0,0.35) 0.4px, transparent 1.3px);
  background-size: 40px 40px, 55px 55px, 47px 47px, 62px 62px, 33px 33px, 51px 51px, 44px 44px, 58px 58px;
}
main {
  max-width: 42rem;
  margin: 0 auto;
  padding: 24px 22px 44px;
}
a { color: #f01a8b; text-decoration: none; }
a:hover { color: #b8106a; }

/* Logo mark */
.brand { padding: 8px 0 4px; }
.brand-line {
  font-family: 'Big Shoulders Stencil Display', 'Impact', sans-serif;
  font-weight: 900;
  font-size: 44px;
  line-height: 0.85;
  letter-spacing: -0.5px;
  color: transparent;
  -webkit-text-stroke: 1.5px #0a0a0a;
  display: flex;
  align-items: center;
}
.brand-line svg { margin: 0 -1px 0 -2px; flex-shrink: 0; }

/* Index title tag */
.title-tag {
  margin-top: 18px;
  display: inline-block;
  background: #0a0a0a;
  padding: 4px 14px 6px;
  transform: rotate(-1.5deg);
}
.title-tag h1 {
  margin: 0;
  font-family: 'Big Shoulders Stencil Display', 'Impact', sans-serif;
  font-weight: 800;
  color: #f2ede4;
  font-size: 36px;
  letter-spacing: 4px;
}
.meta-strip {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.count-tag {
  background: #f01a8b;
  color: #0a0a0a;
  padding: 2px 8px 3px;
  font-family: 'Special Elite', monospace;
  font-size: 11px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  transform: rotate(1deg);
  display: inline-block;
}
.dash-rule {
  flex: 1;
  border-top: 2px dashed #0a0a0a;
  opacity: 0.4;
}
.hint {
  font-family: 'Special Elite', monospace;
  font-size: 10px;
  opacity: 0.55;
}

/* TOC */
ol.toc {
  list-style: none;
  padding: 0;
  margin: 22px 0 0;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
ol.toc li { border-bottom: 1.5px solid #0a0a0a; }
ol.toc li:last-child { border-bottom: none; }
ol.toc a {
  display: flex;
  align-items: baseline;
  gap: 14px;
  padding: 10px 6px;
  color: inherit;
}
ol.toc a:active { opacity: 0.6; }
ol.toc .num {
  font-family: 'Big Shoulders Stencil Display', 'Impact', sans-serif;
  font-weight: 900;
  color: #f01a8b;
  font-size: 38px;
  line-height: 0.85;
  min-width: 38px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
ol.toc .title {
  font-family: 'Big Shoulders Stencil Text', 'Impact', sans-serif;
  font-weight: 700;
  font-size: 20px;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  line-height: 1.05;
}

/* Hymn page */
.hymn-nav-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0 12px;
}
.back-tag {
  font-family: 'Special Elite', monospace;
  font-size: 12px;
  background: #0a0a0a;
  color: #f2ede4 !important;
  padding: 3px 10px 4px;
  letter-spacing: 1px;
}
.song-num {
  font-family: 'Big Shoulders Stencil Display', 'Impact', sans-serif;
  font-weight: 900;
  font-size: 32px;
  line-height: 0.85;
  color: #f01a8b;
}
article {
  padding: 14px 0 4px;
  border-bottom: 3px solid #0a0a0a;
}
article h1 {
  margin: 0;
  font-family: 'Big Shoulders Stencil Display', 'Impact', sans-serif;
  font-weight: 900;
  font-size: 52px;
  line-height: 0.9;
  text-transform: uppercase;
  color: transparent;
  -webkit-text-stroke: 2px #0a0a0a;
}
.verses { padding-top: 6px; }
.verse {
  display: flex;
  gap: 14px;
  padding: 18px 2px 6px;
  align-items: flex-start;
}
.verse.chorus {
  border-left: 3px solid #f01a8b;
  margin-left: -8px;
  padding-left: 10px;
}
.verse.chorus .v-body { font-style: italic; }
.v-label {
  font-family: 'Big Shoulders Stencil Display', 'Impact', sans-serif;
  font-weight: 900;
  color: #f01a8b;
  font-size: 42px;
  line-height: 0.8;
  min-width: 42px;
  text-align: right;
  padding-top: 2px;
  text-transform: uppercase;
}
.v-body {
  flex: 1;
  font-family: 'Special Elite', 'Courier New', monospace;
  font-size: 15px;
  line-height: 1.65;
  color: #0a0a0a;
}
.v-body .line { /* each lyric line; padding kicks in only on print */ }

/* Hide print-only elements on screen */
.print-slug, .print-song-head { display: none; }

/* Footer nav */
.foot {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  gap: 8px;
  padding: 24px 0 0;
  margin-top: 24px;
  border-top: 3px solid #0a0a0a;
  font-family: 'Special Elite', monospace;
  font-size: 12px;
}
.foot a, .foot span { color: inherit; padding: 3px 10px; }
.foot .nav-prev { justify-self: start; }
.foot .home { justify-self: center; }
.foot .nav-next {
  justify-self: end;
  background: #0a0a0a;
  color: #f2ede4 !important;
  padding: 3px 10px 4px;
  letter-spacing: 1px;
}

/* Blank/404 */
.blank {
  text-align: center;
  padding: 6rem 1rem;
  color: rgba(0,0,0,0.55);
  font-family: 'Special Elite', monospace;
}
.blank h1 { font-weight: 500; font-size: 1.2rem; margin: 0 0 0.5rem; }
.blank p { font-size: 0.95rem; margin: 0; }

/* Zine link — pink chip floating top-right of the TOC page */
main { position: relative; }
.zine-link {
  position: absolute;
  top: 44px;
  right: 22px;
  font-family: 'Special Elite', 'Courier New', monospace;
  font-size: 11px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #0a0a0a !important;
  padding: 4px 10px 5px;
  background: #f01a8b;
  transform: rotate(2deg);
  display: inline-block;
  z-index: 2;
}

/* Zine page */
.zine-meta {
  font-family: 'Special Elite', monospace;
  font-size: 10px;
  opacity: 0.55;
  margin-top: 8px;
}
.zine-section {
  padding: 22px 0 20px;
  border-bottom: 2px solid #0a0a0a;
}
.zine-section:last-of-type { border-bottom: none; padding-bottom: 6px; }
.zine-heading {
  margin: 0 0 14px;
  font-family: 'Big Shoulders Stencil Display', 'Impact', sans-serif;
  font-weight: 900;
  font-size: 30px;
  line-height: 0.95;
  letter-spacing: 0.5px;
  text-transform: uppercase;
  color: #0a0a0a;
}
.zine-body {
  font-family: 'Special Elite', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #0a0a0a;
}
.zine-body p { margin: 0 0 12px; }
.zine-body p:last-child { margin-bottom: 0; }
.zine-body ul { margin: 0 0 12px; padding-left: 22px; }
.zine-body li { margin: 4px 0; padding-left: 4px; }
.zine-body li::marker { color: #f01a8b; }

/* Musician's booklet link at bottom of TOC */
.foot-actions {
  margin-top: 28px;
  padding-top: 16px;
  border-top: 1.5px dashed rgba(10,10,10,0.35);
  text-align: right;
}
.foot-link {
  font-family: 'Special Elite', monospace;
  font-size: 11px;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: #0a0a0a !important;
  padding: 4px 10px 5px;
  background: #f01a8b;
  display: inline-block;
  transform: rotate(-1deg);
}

/* QR page */
.qr-wrap { text-align: center; padding: 2rem 0; }
.qr-wrap img {
  max-width: 320px;
  width: 100%;
  height: auto;
  background: white;
  padding: 12px;
}
.qr-wrap p { font-family: 'Special Elite', monospace; font-size: 0.95rem; }
.qr-wrap code {
  font-family: 'Special Elite', monospace;
  font-size: 0.95rem;
  background: rgba(0,0,0,0.08);
  padding: 0.2rem 0.5rem;
  word-break: break-all;
}

/* ────────────────────────────────────────────────────────────
   PRINT STYLES — for musicians who want to write chords above
   each lyric line. Kicks in only when Cmd+P / Print is used.
   ──────────────────────────────────────────────────────────── */
@media print {
  html, body {
    background: #ffffff !important;
    background-image: none !important;
    color: #000000 !important;
  }
  main { max-width: none; padding: 0.55in 0.7in 0.55in 0.95in; }

  /* Hide screen chrome we don't want on paper */
  .brand, .title-tag, .meta-strip,
  .hymn-nav-top, .foot,
  .print-only-web { display: none !important; }

  /* Per-hymn title block */
  article {
    border-bottom: 2pt solid #000 !important;
    padding: 0 0 8pt !important;
    margin-bottom: 6pt;
  }
  article h1 {
    -webkit-text-stroke: 0 !important;
    color: #000 !important;
    font-family: 'Special Elite', 'Courier New', monospace !important;
    font-weight: 400;
    font-size: 22pt;
    line-height: 1.15;
    letter-spacing: 0.5pt;
  }
  .print-slug {
    display: block !important;
    font-family: 'Special Elite', monospace;
    font-size: 10pt;
    letter-spacing: 2pt;
    text-transform: uppercase;
    color: #000;
    margin-bottom: 4pt;
  }

  /* Verse blocks — keep each verse on one page if possible */
  .verse {
    display: flex;
    align-items: flex-start;
    gap: 14pt;
    padding: 4pt 0 6pt;
    break-inside: avoid-page;
    page-break-inside: avoid;
  }
  .verse.chorus {
    border-left: 2pt solid #000 !important;
    margin-left: -8pt;
    padding-left: 10pt;
  }
  .verse.chorus .v-body { font-style: italic; }

  .v-label {
    font-family: 'Special Elite', monospace !important;
    color: #000 !important;
    -webkit-text-stroke: 0 !important;
    font-weight: 700;
    font-size: 15pt;
    line-height: 1;
    min-width: 22pt;
    padding-top: 20pt;   /* aligns label baseline with first lyric line under chord space */
    text-align: right;
  }
  .v-body {
    font-family: 'Special Elite', 'Courier New', monospace !important;
    font-size: 12pt !important;
    color: #000 !important;
    line-height: 1.2;
  }

  /* THE KEY BIT: blank space above every lyric line for handwriting chords */
  .v-body .line {
    padding-top: 20pt;
    line-height: 1.2;
  }

  /* Multi-hymn print page: page-break between songs */
  .print-song { break-after: page; page-break-after: always; }
  .print-song:last-child { break-after: auto; page-break-after: auto; }

  /* On the multi-hymn print page, dim the header of each song a little */
  .print-song-head {
    display: flex !important;
    justify-content: space-between;
    align-items: baseline;
    font-family: 'Special Elite', monospace;
    font-size: 10pt;
    color: #000;
    margin-bottom: 6pt;
  }
}
"""

# The GRACE H⊕USE brand mark, rendered inline. The 8-spoke wheel
# replaces the O in HOUSE.
BRAND_LOGO = """<div class="brand">
  <div class="brand-line">GRACE</div>
  <div class="brand-line">
    <span>H</span>
    <svg width="34" height="34" viewBox="0 0 34 34" aria-label="wheel">
      <circle cx="17" cy="17" r="13" stroke="#0a0a0a" stroke-width="1.8" fill="none"/>
      <line x1="17" y1="4" x2="17" y2="30" stroke="#0a0a0a" stroke-width="1.5"/>
      <line x1="4" y1="17" x2="30" y2="17" stroke="#0a0a0a" stroke-width="1.5"/>
      <line x1="7.81" y1="7.81" x2="26.19" y2="26.19" stroke="#0a0a0a" stroke-width="1.5"/>
      <line x1="26.19" y1="7.81" x2="7.81" y2="26.19" stroke="#0a0a0a" stroke-width="1.5"/>
      <circle cx="17" cy="17" r="2.5" fill="#0a0a0a"/>
    </svg>
    <span>USE</span>
  </div>
</div>"""


def page(title_text: str, body_html: str, key: str) -> str:
    base = f"/{key}/"
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        '<meta name="theme-color" content="#f2ede4">\n'
        f'<base href="{escape(base)}">\n'
        f"<title>{escape(title_text)}</title>\n"
        '<link rel="stylesheet" href="style.css">\n'
        "</head>\n"
        "<body>\n"
        "<main>\n"
        f"{body_html}\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )


def render_toc(hymns, key: str) -> str:
    items = "\n".join(
        f'<li><a href="hymn/{n}">'
        f'<span class="num">{n}</span>'
        f'<span class="title">{escape(t)}</span>'
        f"</a></li>"
        for (n, t, _) in hymns
    )
    # Zine link (only shown if zine.txt exists)
    zine_link = ""
    zine = parse_zine()
    if zine is not None:
        zine_title, _ = zine
        zine_link = f'<a href="zine" class="zine-link">{escape(zine_title.upper())} →</a>'
    body = (
        f"{zine_link}\n"
        f"{BRAND_LOGO}\n"
        '<div class="title-tag"><h1>HYMNAL</h1></div>\n'
        '<div class="meta-strip">'
        f'<span class="count-tag">{len(hymns)} songs</span>'
        '<div class="dash-rule"></div>'
        '<span class="hint">↓ tap one</span>'
        "</div>\n"
        f'<ol class="toc">\n{items}\n</ol>\n'
        '<div class="foot-actions">'
        '<a href="print" class="foot-link">Musician\'s booklet →</a>'
        "</div>"
    )
    return page("Grace House Hymnal", body, key)


def render_zine_body(lines):
    """Render body lines. Consecutive lines starting with '- ' or '* '
    become a <ul>. Other lines are paragraphs."""
    parts = []
    bullets = []

    def flush_bullets():
        if bullets:
            items_html = "".join(f"<li>{escape(b)}</li>" for b in bullets)
            parts.append(f"<ul>{items_html}</ul>")
            bullets.clear()

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if (stripped.startswith("- ") or stripped.startswith("* ")):
            bullets.append(stripped[2:].strip())
        else:
            flush_bullets()
            parts.append(f"<p>{escape(stripped)}</p>")
    flush_bullets()
    return "\n".join(parts)


def render_zine_page(title, sections, key):
    if not sections:
        sections_html = '<p style="opacity:0.5;padding:2rem 0;">Nothing to say yet. Edit zine.txt to add sections.</p>'
    else:
        sections_html = "\n".join(
            f'<section class="zine-section">'
            f'<h2 class="zine-heading">{escape(h)}</h2>'
            f'<div class="zine-body">{render_zine_body(body_lines)}</div>'
            f'</section>'
            for h, body_lines in sections
        )
    # Last-updated date from zine.txt mtime
    updated = ""
    try:
        import datetime
        mtime = datetime.datetime.fromtimestamp(ZINE_PATH.stat().st_mtime)
        updated = mtime.strftime("Updated %b %-d, %Y")
    except Exception:
        pass
    body = (
        '<div class="hymn-nav-top">'
        '<a href="." class="back-tag">← HYMNAL</a>'
        '<span class="song-num">✦</span>'
        "</div>\n"
        f"{BRAND_LOGO}\n"
        f'<div class="title-tag"><h1>{escape(title.upper())}</h1></div>\n'
        '<div class="meta-strip">'
        f'<span class="count-tag">{escape(updated) if updated else "the zine"}</span>'
        '<div class="dash-rule"></div>'
        '<span class="hint">↓ read</span>'
        "</div>\n"
        f'<div class="zine-content">\n{sections_html}\n</div>'
    )
    return page(f"{title} — Grace House", body, key)


def _verse_block_html(label: str, lines: list[str]) -> str:
    is_chorus = label.upper() == "C"
    chorus_cls = " chorus" if is_chorus else ""
    body_html = "\n".join(
        f'<div class="line">{escape(ln)}</div>' for ln in lines
    )
    return (
        f'<section class="verse{chorus_cls}">'
        f'<span class="v-label">{escape(label)}</span>'
        f'<div class="v-body">{body_html}</div>'
        f'</section>'
    )


def render_hymn_page(number, title, verses, prev_n, next_n, key: str) -> str:
    verse_html = "\n".join(_verse_block_html(label, lines) for label, lines in verses)
    prev_link = (
        f'<a class="nav-prev" href="hymn/{prev_n}">← PREV</a>'
        if prev_n else '<span></span>'
    )
    next_link = (
        f'<a class="nav-next" href="hymn/{next_n}">NEXT →</a>'
        if next_n else '<span></span>'
    )
    body = (
        '<div class="hymn-nav-top">'
        '<a href="." class="back-tag">← ALL HYMNS</a>'
        f'<span class="song-num">#{number}</span>'
        "</div>\n"
        "<article>\n"
        f'<span class="print-slug">Song #{number}</span>'
        f"<h1>{escape(title)}</h1>\n"
        "</article>\n"
        f'<div class="verses">\n{verse_html}\n</div>\n'
        '<nav class="foot">\n'
        f"{prev_link}\n"
        '<a class="home" href=".">INDEX</a>\n'
        f"{next_link}\n"
        "</nav>"
    )
    return page(f"{title} — Grace House Hymnal", body, key)


def render_print_all(hymns, key: str) -> str:
    """Render every hymn on one long page with page-breaks between them —
    for printing the whole booklet at once."""
    songs_html = []
    for (number, _t, filepath) in hymns:
        title, verses = parse_hymn(filepath)
        verse_html = "\n".join(_verse_block_html(l, ls) for l, ls in verses)
        songs_html.append(
            '<section class="print-song">\n'
            '<div class="print-song-head">'
            f'<span>Grace House Hymnal</span>'
            f'<span>#{number}</span>'
            "</div>\n"
            "<article>\n"
            f'<span class="print-slug">Song #{number}</span>'
            f"<h1>{escape(title)}</h1>\n"
            "</article>\n"
            f'<div class="verses">\n{verse_html}\n</div>\n'
            "</section>"
        )
    all_html = "\n".join(songs_html)
    # Screen intro (hidden on print) — shows a friendly "hit Cmd+P" note
    screen_intro = (
        '<div class="print-only-web" style="padding: 24px 0; border-bottom: 3px solid #0a0a0a; margin-bottom: 24px;">'
        f'{BRAND_LOGO}'
        '<div class="title-tag" style="margin-top: 14px;"><h1>PRINT BOOKLET</h1></div>'
        '<p style="font-family:\'Special Elite\',monospace;font-size:14px;margin-top:16px;line-height:1.5;">'
        f'All {len(hymns)} songs, formatted for printing. Each song gets its own page '
        'with blank space above every lyric line for handwritten chords. '
        'Press <strong>Cmd+P</strong> (or your browser\'s print menu) to print, '
        'or use "Save as PDF" to keep a digital copy.'
        '</p>'
        '<p style="font-family:\'Special Elite\',monospace;font-size:12px;margin-top:12px;opacity:0.7;">'
        '<a href=".">← back to hymnal</a>'
        '</p>'
        '</div>'
    )
    return page("Print Booklet — Grace House Hymnal", screen_intro + all_html, key)


def render_qr_page(url: str, have_png: bool, key: str) -> str:
    if have_png:
        img = '<img src="qr-code.png" alt="QR code">'
    else:
        img = "<p><em>qr-code.png not found.</em></p>"
    body = (
        '<div class="hymn-nav-top">'
        '<a href="." class="back-tag">← ALL HYMNS</a>'
        '<span class="song-num">QR</span>'
        "</div>\n"
        '<div class="qr-wrap">\n'
        f"{img}\n"
        f"<p>Points to <code>{escape(url)}</code></p>\n"
        "</div>"
    )
    return page("QR — Grace House Hymnal", body, key)


def render_blank() -> str:
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Not found</title>\n"
        "<style>\n" + CSS + "\n</style>\n"
        "</head><body>\n"
        '<main><div class="blank">\n'
        "<h1>Nothing here.</h1>\n"
        "<p>If you're expecting to see something, ask whoever shared the link with you.</p>\n"
        "</div></main>\n"
        "</body></html>\n"
    )


# ─────────────────────────────────────────────────────────────
# Server

class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "Hymnal/1.1"

    def log_message(self, fmt, *args):
        pass

    def _send(self, body: bytes, ctype: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str):
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _blank(self):
        self._send(render_blank().encode("utf-8"), "text/html; charset=utf-8", 404)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        key = load_key()
        prefix = f"/{key}"

        if path == prefix:
            self._redirect(prefix + "/")
            return
        if not path.startswith(prefix + "/"):
            self._blank()
            return

        inner = path[len(prefix):]

        if inner == "/style.css":
            self._send(CSS.encode("utf-8"), "text/css; charset=utf-8")
            return
        if inner == "/qr-code.png":
            if QR_PATH.exists():
                self._send(QR_PATH.read_bytes(), "image/png")
            else:
                self._send(b"QR not found", "text/plain; charset=utf-8", 404)
            return
        if inner == "/qr":
            port = self.server.server_address[1]
            url = f"http://localhost:{port}{prefix}/"
            self._send(
                render_qr_page(url, QR_PATH.exists(), key).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if inner == "/":
            hymns = load_hymns()
            self._send(
                render_toc(hymns, key).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if inner == "/print":
            hymns = load_hymns()
            self._send(
                render_print_all(hymns, key).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        if inner == "/zine":
            zine = parse_zine()
            if zine is None:
                self._blank()
                return
            title, sections = zine
            self._send(
                render_zine_page(title, sections, key).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        m = re.match(r"^/hymn/(\d+)$", inner)
        if m:
            wanted = int(m.group(1))
            hymns = load_hymns()
            idx = next((i for i, (n, _, _) in enumerate(hymns) if n == wanted), None)
            if idx is None:
                self._blank()
                return
            number, title, filepath = hymns[idx]
            title, verses = parse_hymn(filepath)
            prev_n = hymns[idx - 1][0] if idx > 0 else None
            next_n = hymns[idx + 1][0] if idx < len(hymns) - 1 else None
            self._send(
                render_hymn_page(number, title, verses, prev_n, next_n, key).encode("utf-8"),
                "text/html; charset=utf-8",
            )
            return
        self._blank()


class ReuseTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    port = DEFAULT_PORT
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Bad port: {sys.argv[1]}")
            sys.exit(2)

    if not HYMNS_DIR.exists():
        HYMNS_DIR.mkdir()

    key = load_key()

    bar = "─" * 62
    print()
    print(bar)
    print("  Grace House Hymnal is running")
    print(bar)
    print(f"  On this Mac       :  http://localhost:{port}/{key}/")
    print(f"  Print the QR code :  http://localhost:{port}/{key}/qr")
    print()
    print(f"  Access key        :  {key}")
    print(f"  (edit access-key.txt to change; then regenerate QR)")
    print()
    print(f"  Phones reach this via your Tailscale Funnel URL.")
    print(f"  Make sure Tailscale + Funnel are running.")
    print()
    print(f"  Hymns are loaded from ./hymns  (see SETUP for format)")
    print(f"  Press Ctrl+C to stop.")
    print(bar)
    print()

    try:
        with ReuseTCPServer(("0.0.0.0", port), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    except OSError as e:
        print(f"\nCouldn't start server: {e}")
        print(f"Another program may be using port {port}.")
        print(f"Try:  python3 server.py 8080")
        sys.exit(1)


if __name__ == "__main__":
    main()
