# Raghavendra Kotikalapudi

Static academic profile for [raghakot.com](https://raghakot.com). No build step is required.

Run a local preview from the repository root:

```sh
python3 -m http.server 8000 --bind 127.0.0.1
```

Open <http://127.0.0.1:8000/>. The page also works when opening `index.html` directly.

- `index.html` contains the profile, publications, highlights, and patents.
- `styles.css` contains the palette, shared layouts, responsive rules, and print styles.
- `script.js` marks the current navigation section and expands the archive for printing.
- `fonts/` contains the local fonts and their licenses; `favicon.svg` contains the tab icon.

The citation updater runs every Monday at 00:00 UTC through
`.github/workflows/update-citations.yml`. It uses the repository's `SCRAPERAPI_KEY`
secret to access Google Scholar, then commits and pushes citation changes.

Set up the Python environment and run the offline regression checks:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r scripts/requirements.txt
.venv/bin/python -m unittest discover -s scripts -p 'test_*.py'
```

For a manual citation refresh, run `.venv/bin/python scripts/update_citations.py`.
Local requests may need `SCRAPERAPI_KEY` in the environment if Scholar blocks direct access.
Counts retain the existing rounding policy and never decrease; fetch failures leave
the page unchanged and return a failing exit status.

Publication titles use the `publication-title` class, and existing counts use
`publication-citations`. Keep those hooks when editing the markup so the updater
can associate each count with its paper.
