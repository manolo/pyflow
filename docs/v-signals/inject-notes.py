#!/usr/bin/env python3
"""inject-notes.py: sync speaker notes between .md and HTML.

Usage:
  ./inject-notes.py es              Inject v-signals-notes-es.md into v-signals-es.html
  ./inject-notes.py en              Inject v-signals-notes-en.md into v-signals.html
  ./inject-notes.py all             Both languages
  ./inject-notes.py extract es      One-off: extract HTML notes into the .md file

Markdown format (each slide is one section):

    ## Slide 1: Title

    - First paragraph.
    - Second paragraph.

    ## Slide 2: Hook

    - ...

Bullets become <p> tags inside <aside class="notes">.
Order matters: section N in the .md → Nth <aside> in the HTML.
"""

import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

LANG_TO_HTML = {
    "es": BASE / "v-signals-es.html",
    "en": BASE / "v-signals.html",
}
LANG_TO_MD = {
    "es": BASE / "v-signals-notes-es.md",
    "en": BASE / "v-signals-notes-en.md",
}

ASIDE_RE = re.compile(
    r'(<aside class="notes">)(.*?)(</aside>)',
    re.DOTALL,
)
HEADING_RE = re.compile(r'^## Slide \d+.*$', re.MULTILINE)
SECTION_RE = re.compile(r'<section\b[^>]*>(.*?)</section>', re.DOTALL)
TITLE_TAG_RE = re.compile(r'<h[12][^>]*>(.*?)</h[12]>', re.DOTALL)


def strip_html(s: str) -> str:
    """Remove tags and entities for a clean .md heading title."""
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace("&middot;", "·").replace("&mdash;", "—").replace("&amp;", "&")
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def parse_md(md_text: str) -> list[list[str]]:
    """Return list of paragraph lists, one per slide section in order."""
    parts = HEADING_RE.split(md_text)[1:]
    out = []
    for body in parts:
        paragraphs = []
        for line in body.splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                paragraphs.append(stripped[2:].strip())
        out.append(paragraphs)
    return out


def inject(html: str, notes: list[list[str]]) -> tuple[str, int]:
    counter = [0]
    warnings = 0

    def replace(match):
        nonlocal warnings
        idx = counter[0]
        counter[0] += 1
        if idx >= len(notes):
            warnings += 1
            print(f"  warn: HTML has more <aside> blocks than .md sections at slide {idx + 1}", file=sys.stderr)
            return match.group(0)
        paragraphs = notes[idx]
        body_lines = "\n".join(f"          <p>{p}</p>" for p in paragraphs)
        return f"{match.group(1)}\n{body_lines}\n        {match.group(3)}"

    new_html = ASIDE_RE.sub(replace, html)
    if counter[0] < len(notes):
        print(f"  warn: .md has {len(notes)} sections but HTML has only {counter[0]} <aside> blocks", file=sys.stderr)
        warnings += 1
    return new_html, warnings


def extract(html: str) -> list[tuple[str, list[str]]]:
    """Return list of (slide_title, paragraphs[]) tuples.

    Walks each <section> and pairs its h1/h2 with its <aside class="notes">.
    Sections without an aside are skipped.
    """
    sections = []
    for sec_match in SECTION_RE.finditer(html):
        section_body = sec_match.group(1)
        aside_match = ASIDE_RE.search(section_body)
        if not aside_match:
            continue
        title_match = TITLE_TAG_RE.search(section_body)
        title = strip_html(title_match.group(1)) if title_match else ""
        body = aside_match.group(2)
        paragraphs = re.findall(r'<p>(.*?)</p>', body, re.DOTALL)
        paragraphs = [re.sub(r'\s+', ' ', p).strip() for p in paragraphs]
        if not paragraphs:
            clean = re.sub(r'\s+', ' ', body).strip()
            if clean:
                paragraphs = [clean]
        sections.append((title, paragraphs))
    return sections


def cmd_inject(lang: str) -> int:
    md_path = LANG_TO_MD[lang]
    html_path = LANG_TO_HTML[lang]
    if not md_path.exists():
        print(f"  error: {md_path.name} not found. Run with 'extract {lang}' first.", file=sys.stderr)
        return 1
    if not html_path.exists():
        print(f"  error: {html_path.name} not found.", file=sys.stderr)
        return 1
    notes = parse_md(md_path.read_text())
    new_html, warnings = inject(html_path.read_text(), notes)
    html_path.write_text(new_html)
    suffix = f" ({warnings} warnings)" if warnings else ""
    print(f"  injected {len(notes)} notes into {html_path.name}{suffix}")
    return 0


def cmd_extract(lang: str) -> int:
    html_path = LANG_TO_HTML[lang]
    md_path = LANG_TO_MD[lang]
    if not html_path.exists():
        print(f"  error: {html_path.name} not found.", file=sys.stderr)
        return 1
    sections = extract(html_path.read_text())
    lines = [f"# Speaker notes for {html_path.name}", ""]
    lines.append(f"_Auto-extracted from `{html_path.name}`: edit me, then run `./inject-notes.py {lang}`._")
    lines.append("")
    for idx, (title, paragraphs) in enumerate(sections, start=1):
        suffix = f": {title}" if title else ""
        lines.append(f"## Slide {idx}{suffix}")
        lines.append("")
        if not paragraphs:
            lines.append("- (empty)")
        for p in paragraphs:
            lines.append(f"- {p}")
        lines.append("")
    md_path.write_text("\n".join(lines))
    print(f"  extracted {len(sections)} notes into {md_path.name}")
    return 0


def usage() -> int:
    print(__doc__, file=sys.stderr)
    return 1


def main() -> int:
    args = sys.argv[1:]
    if not args:
        return usage()

    # Allow either: "inject-notes.py es" or "inject-notes.py extract es"
    if args[0] in ("extract",):
        if len(args) < 2:
            return usage()
        targets = [args[1]] if args[1] != "all" else ["es", "en"]
        rc = 0
        for lang in targets:
            if lang not in LANG_TO_HTML:
                print(f"  unknown lang: {lang}", file=sys.stderr)
                return 1
            rc |= cmd_extract(lang)
        return rc

    targets = [args[0]] if args[0] != "all" else ["es", "en"]
    rc = 0
    for lang in targets:
        if lang not in LANG_TO_HTML:
            print(f"  unknown lang: {lang}", file=sys.stderr)
            return 1
        rc |= cmd_inject(lang)
    return rc


if __name__ == "__main__":
    sys.exit(main())
