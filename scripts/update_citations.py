#!/usr/bin/env python3
"""Fetch citation counts from Google Scholar and update index.html.

Non-destructive: only updates when the new count >= currently displayed count.
Rounds down to the nearest 10 for display.
"""

import os
import re
import sys
from pathlib import Path

from scholarly import ProxyGenerator, scholarly

SCHOLAR_ID = "g2UodAsAAAAJ"
HTML_FILE = Path(__file__).resolve().parent.parent / "index.html"


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
    """Round to the nearest bucket; bucket grows with magnitude.

    Uses nearest (not floor) so a count just below a milestone snaps
    up -- 990 displays as 1,000+ since citations will catch up shortly,
    and 948 displays as 950+ rather than the more misleading 900+.
    Buckets stay small for low counts so we don't lop off a meaningful
    percentage (bucket 10 for 73 -> 70, not bucket 50 -> 50).
    """
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


def title_similarity(t1, t2):
    w1 = set(re.findall(r"\w+", t1.lower()))
    w2 = set(re.findall(r"\w+", t2.lower()))
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / max(len(w1), len(w2))


def fetch_scholar_citations():
    author = scholarly.search_author_id(SCHOLAR_ID)
    author = scholarly.fill(author, sections=["publications"])

    results = {}
    for pub in author["publications"]:
        title = pub["bib"].get("title", "")
        citations = pub.get("num_citations", 0)
        results[title] = citations

    return results


def main():
    html = HTML_FILE.read_text()

    setup_proxy()

    print("Fetching citations from Google Scholar...")
    try:
        scholar_data = fetch_scholar_citations()
    except Exception as e:
        print(f"Error fetching from Scholar: {e}")
        print("Skipping this run; will retry on next schedule.")
        sys.exit(0)

    print(f"Found {len(scholar_data)} publications on Scholar.\n")

    # Match publication titles in HTML to their citation spans. The tempered
    # dot keeps each match inside one <li>, so an entry without a citations
    # span can never pair its title with a later entry's span.
    pattern = re.compile(
        r'(<a[^>]*class="publication-title">)(.*?)(</a>(?:(?!</li>).)*?'
        r'<span class="publication-citations">)(.*?)(</span>)',
        re.DOTALL,
    )

    updated = False

    def replacer(match):
        nonlocal updated
        title = match.group(2).strip()
        current_text = match.group(4).strip()
        current_count = parse_displayed_count(current_text)

        best_title, best_score = None, 0
        for scholar_title in scholar_data:
            score = title_similarity(title, scholar_title)
            if score > best_score:
                best_score = score
                best_title = scholar_title

        if best_title and best_score > 0.5:
            new_count = scholar_data[best_title]
            new_rounded = round_citations(new_count)
            if new_rounded >= current_count:
                new_text = format_citations(new_count)
                if new_text != current_text:
                    print(f"  Updated: {title}")
                    print(f"    {current_text} -> {new_text} (raw: {new_count})")
                    updated = True
                    return (
                        match.group(1)
                        + match.group(2)
                        + match.group(3)
                        + new_text
                        + match.group(5)
                    )
                else:
                    print(f"  No change: {title} ({current_text})")
            else:
                print(
                    f"  Skipped (would decrease): {title} "
                    f"({current_count} -> {new_rounded})"
                )
        else:
            print(f"  No Scholar match: {title}")

        return match.group(0)

    new_html = pattern.sub(replacer, html)

    if updated:
        HTML_FILE.write_text(new_html)
        print("\nindex.html updated.")
    else:
        print("\nNo updates needed.")


if __name__ == "__main__":
    main()
