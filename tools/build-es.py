#!/usr/bin/env python3
"""Generate es/index.html from index.html.

Why this exists
---------------
Both languages used to live on one URL, with the Spanish half hidden by
`display:none`. Search engines largely discount hidden text, so the Spanish
copy was effectively invisible — a problem when LatAm is a target market.

Rather than hand-maintaining a second page (which would drift, the way the
changelog section drifted from update.json), the Spanish page is generated
from the English one. `index.html` stays the single file anyone edits.

What it does
------------
  * drops every `data-lang="en"` element
  * unhides every `data-lang="es"` element
  * switches lang, canonical, og:locale and the social text to Spanish
  * adds hreflang links tying the two pages together
  * rewrites root-relative asset paths so they resolve from /es/
  * points the language picker at the other URL instead of toggling in place

Run:    python3 tools/build-es.py
Check:  python3 tools/build-es.py --check     (used by CI; non-zero if stale)
"""

from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SOURCE = ROOT / "index.html"
OUTPUT = ROOT / "es" / "index.html"

SITE = "https://www.smartsubcrates.com"

ES_TITLE = "Smart Subcrates — Crea Subcrates de Serato desde tus Carpetas"
ES_DESCRIPTION = (
    "Convierte tus carpetas de música en subcrates listos para Serato en segundos. "
    "Para macOS 12+ (Apple Silicon + Intel). Pago único, actualizaciones de por vida."
)
ES_OG_DESCRIPTION = (
    "Crea subcrates de Serato desde tus carpetas con un clic. Para macOS 12+."
)


def drop_english_blocks(html: str) -> str:
    """Remove elements marked data-lang="en" entirely."""
    # Matches a tag carrying data-lang="en" through its matching close tag.
    # The markup here is flat (no data-lang element nests another), so a
    # non-greedy match to the next matching close tag is correct.
    pattern = re.compile(
        r'<(?P<tag>[a-zA-Z0-9]+)(?P<attrs>[^>]*\bdata-lang="en"[^>]*)>'
        r'(?P<body>.*?)</(?P=tag)>',
        re.DOTALL,
    )
    previous = None
    while previous != html:
        previous = html
        html = pattern.sub("", html, count=1)
    # Self-closing / void elements carrying data-lang="en"
    html = re.sub(r'<(?:img|br|input|source)[^>]*\bdata-lang="en"[^>]*/?>', "", html)
    return html


def reveal_spanish_blocks(html: str) -> str:
    """Make data-lang="es" elements visible: they ship hidden on the English page."""
    def fix(match: re.Match) -> str:
        tag = match.group(0)
        # strip display:none from an inline style, then drop an empty style=""
        tag = re.sub(r'style="([^"]*)"',
                     lambda m: 'style="%s"' % re.sub(
                         r'\s*display\s*:\s*none\s*;?\s*', '', m.group(1)).strip(),
                     tag)
        tag = re.sub(r'\s*style=""', "", tag)
        return tag

    return re.sub(r'<[a-zA-Z0-9]+[^>]*\bdata-lang="es"[^>]*>', fix, html)


def localise_head(html: str) -> str:
    html = html.replace('<html lang="en">', '<html lang="es">', 1)

    html = re.sub(r"<title>.*?</title>", f"<title>{ES_TITLE}</title>", html, count=1, flags=re.DOTALL)
    html = re.sub(r'(<meta name="description" content=")[^"]*(")',
                  rf"\g<1>{ES_DESCRIPTION}\g<2>", html, count=1)

    html = html.replace(f'<link rel="canonical" href="{SITE}/" />',
                        f'<link rel="canonical" href="{SITE}/es/" />', 1)
    html = html.replace(f'<meta property="og:url" content="{SITE}/" />',
                        f'<meta property="og:url" content="{SITE}/es/" />', 1)

    for prop, value in (("og:title", ES_TITLE), ("og:description", ES_OG_DESCRIPTION),
                        ("twitter:title", ES_TITLE), ("twitter:description", ES_OG_DESCRIPTION)):
        attr = "property" if prop.startswith("og:") else "name"
        html = re.sub(rf'(<meta {attr}="{prop}" content=")[^"]*(")',
                      rf"\g<1>{value}\g<2>", html, count=1)

    html = html.replace('<meta property="og:locale" content="en_US" />\n  '
                        '<meta property="og:locale:alternate" content="es_ES" />',
                        '<meta property="og:locale" content="es_ES" />\n  '
                        '<meta property="og:locale:alternate" content="en_US" />', 1)
    return html


def add_hreflang(html: str, self_url: str) -> str:
    """Tell search engines these two pages are the same content in two languages."""
    links = (
        f'  <link rel="alternate" hreflang="en" href="{SITE}/" />\n'
        f'  <link rel="alternate" hreflang="es" href="{SITE}/es/" />\n'
        f'  <link rel="alternate" hreflang="x-default" href="{SITE}/" />\n'
    )
    if 'hreflang="en"' in html:
        return html
    return html.replace('  <meta property="og:title"', links + '  <meta property="og:title"', 1)


def fix_asset_paths(html: str) -> str:
    """style.css and script.js are referenced relatively; from /es/ they would
    resolve to /es/style.css. Make them root-relative."""
    html = re.sub(r'href="(style\.css[^"]*)"', r'href="/\1"', html)
    html = re.sub(r'src="(script\.js[^"]*)"', r'src="/\1"', html)
    return html


def point_language_picker(html: str, other_url: str, keep: str) -> str:
    """On a per-language URL the picker should navigate, not toggle in place."""
    old = re.search(r'<select id="language-dropdown".*?</select>', html, re.DOTALL)
    if not old:
        return html
    selected_en = ' selected' if keep == "en" else ""
    selected_es = ' selected' if keep == "es" else ""
    new = (
        '<select id="language-dropdown" class="lang" aria-label="Language" '
        'onchange="if(this.value!==\'%s\')location.href=\'%s\'">\n'
        '          <option value="en"%s>&#127482;&#127480; English</option>\n'
        '          <option value="es"%s>&#127466;&#127464; Espa&ntilde;ol</option>\n'
        '        </select>'
    ) % (keep, other_url, selected_en, selected_es)
    return html[: old.start()] + new + html[old.end():]


def strip_lang_markers(html: str) -> str:
    """Remove every data-lang attribute from the generated page.

    script.js hides any [data-lang] element that does not match the selected
    language. On a Spanish-only page every element is data-lang="es", so a
    visitor whose saved preference was "en" had the entire page hidden — the
    rendered result was a blank layout with only the untagged badges showing.
    Caught by looking at the page, not by parsing it.

    With the markers gone there is nothing for the toggle to act on, which is
    correct: language is chosen by URL here, not by a client-side switch.
    """
    return re.sub(r'\s*data-lang="(?:en|es)"', "", html)


def build() -> str:
    html = SOURCE.read_text(encoding="utf-8")
    html = drop_english_blocks(html)
    html = reveal_spanish_blocks(html)
    html = localise_head(html)
    html = add_hreflang(html, f"{SITE}/es/")
    html = fix_asset_paths(html)
    html = point_language_picker(html, "/", keep="es")
    html = strip_lang_markers(html)
    header = ("<!-- GENERATED from index.html by tools/build-es.py — do not edit. "
              "Edit index.html and re-run the script. -->\n")
    return header + html


def main() -> int:
    generated = build()
    check_only = "--check" in sys.argv

    if check_only:
        if not OUTPUT.exists():
            print("::error::es/index.html is missing. Run: python3 tools/build-es.py")
            return 1
        if OUTPUT.read_text(encoding="utf-8") != generated:
            print("::error file=es/index.html::es/index.html is out of date with "
                  "index.html. Run: python3 tools/build-es.py")
            return 1
        print("es/index.html is up to date")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(generated, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)} ({len(generated) / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
