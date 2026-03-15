#!/usr/bin/env python3
"""Fetch citation counts from Google Scholar and update index.html.

Non-destructive: only updates when the new count >= currently displayed count.
Rounds down to the nearest 10 for display.
"""

import re
import sys
from pathlib import Path

from scholarly import scholarly

SCHOLAR_ID = "g2UodAsAAAAJ"
HTML_FILE = Path(__file__).resolve().parent.parent / "index.html"


def round_citations(count):
    if count < 10:
        return count
    return (count // 10) * 10


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

    print("Fetching citations from Google Scholar...")
    try:
        scholar_data = fetch_scholar_citations()
    except Exception as e:
        print(f"Error fetching from Scholar: {e}")
        sys.exit(1)

    print(f"Found {len(scholar_data)} publications on Scholar.\n")

    # Match publication titles in HTML to their citation spans
    pattern = re.compile(
        r'(<a[^>]*class="publication-title">)(.*?)(</a>.*?'
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
            if new_count >= current_count:
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
                    f"  Skipped (count dropped): {title} "
                    f"({current_count} -> {new_count})"
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
