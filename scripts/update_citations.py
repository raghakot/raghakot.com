#!/usr/bin/env python3
"""Fetch citation counts from Google Scholar and update index.html.

Non-destructive: only updates when the new count >= currently displayed count.
Rounds to magnitude-based buckets for display. Fetch failures leave the page
unchanged and exit unsuccessfully so GitHub Actions reports the failed update.
"""

import os
import re
from html import unescape
from pathlib import Path

from scholarly import ProxyGenerator, scholarly

SCHOLAR_ID = "g2UodAsAAAAJ"
HTML_FILE = Path(__file__).resolve().parent.parent / "index.html"
MIN_TITLE_SIMILARITY = 0.5

# Bound each match to one list item. An uncited paper must never consume the
# next paper's citation span. Named groups keep all surrounding HTML intact.
CITATION_PATTERN = re.compile(
    r'(?P<prefix><a\b[^>]*class="publication-title"[^>]*>'
    r'(?P<title>[^<]*)</a>(?:(?!</li>).)*?'
    r'<span class="publication-citations">)'
    r'(?P<count>[^<]*)(?P<suffix></span>)',
    re.DOTALL,
)


def setup_proxy():
    """Route scholarly through ScraperAPI when SCRAPERAPI_KEY is set.

    Google Scholar blocks bare GitHub Actions runner IPs; ScraperAPI rotates
    residential IPs so the fetch actually succeeds.
    """
    api_key = os.environ.get("SCRAPERAPI_KEY")
    if not api_key:
        print("SCRAPERAPI_KEY not set; trying direct fetch (likely to be blocked).")
        return
    pg = ProxyGenerator()
    if pg.ScraperAPI(api_key):
        scholarly.use_proxy(pg)
        print("Using ScraperAPI proxy.")
    else:
        print("ScraperAPI setup failed; falling back to direct fetch.")


def round_citations(count):
    """Preserve the display's nearest-bucket rounding (73 → 70, 948 → 950)."""
    if count < 10:
        return count
    if count < 100:
        bucket = 10
    elif count < 1000:
        bucket = 50
    elif count < 10000:
        bucket = 100
    else:
        bucket = 500
    return round(count / bucket) * bucket


def format_citations(count):
    rounded = round_citations(count)
    return f"{rounded:,}+ citations"


def parse_displayed_count(text):
    match = re.search(r"([\d,]+)\+?\s*citation", text)
    if match:
        return int(match.group(1).replace(",", ""))
    return 0


def title_similarity(first, second):
    first_words = set(re.findall(r"\w+", unescape(first).lower()))
    second_words = set(re.findall(r"\w+", unescape(second).lower()))
    if not first_words or not second_words:
        return 0.0
    return len(first_words & second_words) / max(len(first_words), len(second_words))


def fetch_scholar_citations():
    author = scholarly.search_author_id(SCHOLAR_ID)
    author = scholarly.fill(author, sections=["publications"])

    return {
        publication["bib"].get("title", ""): publication.get("num_citations", 0)
        for publication in author["publications"]
    }


def update_citations(html, scholar_data):
    """Replace matching citation counts without fetching data or writing files."""
    def replace_citation(match):
        title = match["title"].strip()
        current_text = match["count"].strip()
        current_count = parse_displayed_count(current_text)

        best_title = max(
            scholar_data,
            key=lambda candidate: title_similarity(title, candidate),
            default=None,
        )
        if best_title is None or title_similarity(title, best_title) <= MIN_TITLE_SIMILARITY:
            print(f"  No Scholar match: {title}")
            return match[0]

        new_count = scholar_data[best_title]
        new_rounded = round_citations(new_count)
        if new_rounded < current_count:
            print(f"  Skipped (would decrease): {title} ({current_count} -> {new_rounded})")
            return match[0]

        new_text = format_citations(new_count)
        if new_text == current_text:
            print(f"  No change: {title} ({current_text})")
            return match[0]

        print(f"  Updated: {title}")
        print(f"    {current_text} -> {new_text} (raw: {new_count})")
        return f'{match["prefix"]}{new_text}{match["suffix"]}'

    return CITATION_PATTERN.sub(replace_citation, html)


def main():
    html = HTML_FILE.read_text(encoding="utf-8")

    print("Fetching citations from Google Scholar...")
    try:
        setup_proxy()
        scholar_data = fetch_scholar_citations()
        if not scholar_data:
            raise ValueError("Google Scholar returned no publications")
    except Exception as error:
        print(f"Error fetching from Scholar: {error}")
        print("Page left unchanged; will retry on the next schedule.")
        return 1

    print(f"Found {len(scholar_data)} publications on Scholar.\n")
    new_html = update_citations(html, scholar_data)
    if new_html != html:
        HTML_FILE.write_text(new_html, encoding="utf-8")
        print("\nindex.html updated.")
    else:
        print("\nNo updates needed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
