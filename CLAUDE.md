# CLAUDE.md — CXL Bibliometrics

Standing context for Claude Code sessions in this repo. Read this first.

## What this is

A bibliometric analysis pipeline for the **corneal cross-linking (CXL)**
research literature, 2001–present. It pulls records from PubMed, disambiguates
authors, enriches country + citation data, and produces figures, CSVs, and an
Excel workbook. Output feeds a manuscript targeting the journal **Cornea** (LWW;
editor Prof. Reza Dana) plus its Supplemental Digital Content (SDC).

There is a **sister project**, `kc_biblio` (keratoconus → *Contact Lens &
Anterior Eye*), with near-identical architecture. Changes here often need
porting there and vice versa.

## Environment (important — non-standard)

- **System Python, not a venv.** A `venv/` may appear "active" in the prompt but
  `source venv/bin/activate` fails — it's broken/stale. Treat this as a system
  Python install.
- **pip needs `--break-system-packages`:**
  `python3 -m pip install -r requirements.txt --break-system-packages`
- **Dependencies are minimal — only four:** `numpy`, `matplotlib`, `networkx`,
  `openpyxl`. HTTP uses the **standard-library `urllib`** — do NOT add
  `requests`. `pandas`/`seaborn`/`scipy` are NOT used; don't reintroduce them.
  `pyvis` is optional (interactive network only).
- Verify the environment any time with `python3 check_deps.py`. `main.py` runs
  this guard at startup; `gui.py` warns but still launches.
- **NCBI API key:** read from the `NCBI_API_KEY` env var (or `--api-key`).
  10 req/s with a key, 3 without.

## How to run

```bash
# Full run from a PMID list
python3 main.py --api-key "$NCBI_API_KEY" --pmid-file pmids_expanded.txt

# Reuse cached records + citations (fast; most common during dev)
python3 main.py --skip-fetch --skip-citations

# Single period only, or a custom window
python3 main.py --period last_10yr
python3 main.py --start-year 2010 --end-year 2020

# Local web GUI (multi-period toggle, per-period figure/download browsing)
python3 gui.py        # opens http://localhost:7432

# Synthetic-data smoke test (no network)
python3 demo.py
```

Key flags: `--refresh` (force re-download), `--skip-fetch`, `--skip-citations`,
`--skip-viz`, `--period`, `--start-year`, `--end-year`.

## Architecture

8-step pipeline, one module per concern:

```
fetch.py        PubMed E-utilities (urllib), PMID list or query → records.json cache
disambiguate.py 4-layer author ID (ORCID / forename / co-author overlap / institution);
                KNOWN_DISTINCT safelist separates Seiler T vs TG, Hafezi F vs N;
                KNOWN_DISTINCT_AFFIL blocks the Tehran plastic-surgeon Hafezi
geo.py          country from affiliation strings
citations.py    CrossRef citation counts by DOI (api.crossref.org)
analyze.py      all metrics — temporal, authors, journals, countries, keywords,
                MeSH, institutions (FIRST-AUTHOR attribution), pub_types, languages
periods.py      slices records into config.ANALYSIS_PERIODS, runs analyze+report+viz per window
visualize.py    matplotlib figures (+ optional pyvis network)
report.py       CSVs + multi-sheet Excel workbook
config.py       all knobs (see below)
main.py         CLI orchestration
gui.py          local web server + single-file HTML/JS UI
check_deps.py   startup dependency guard
demo.py         500 synthetic records for testing
```

## config.py essentials

- `ALL_TIME_START = 2001` (CXL literature begins ~2001 — do not lower).
- `END_YEAR = date.today().year` (auto).
- `ANALYSIS_PERIODS`: all_time, last_20/15/10/5yr. **No last_25yr** — for CXL it
  would equal all_time, so it's correctly omitted. (KC *does* have last_25yr.)
- `OUTPUT_DIR = output/` (NOT `outputs/` — an earlier bug; keep it `output`).
  Per-period results land in `output/<period>/`.
- `FIGURE_FORMAT = "pdf"` for CLI (publication-ready). The GUI overrides this to
  `png` so figures render inline in the browser — PDFs won't show in `<img>`.

## Data conventions / facts to preserve

- Definitive clean run (2001–2025): **2,952 publications, 79,807 CrossRef
  citations, mean 27.0 cites/paper**, 288 journals, 53 countries, peak year 2021.
- Institutions use **first-author attribution** (Wenzhou #1 at 36, ELZA #2 at 30).
  An older multi-author method put ELZA #1 at 58 — that method is wrong for this
  analysis; don't revert.
- The citation drop after ~2015 in Figure 1 is **citation accumulation bias**, not
  a real decline. This is documented in the manuscript; keep the explanation if
  touching temporal analysis.
- Languages are stored as ISO 639-2 codes (`eng`, `ger`, …) and mapped to display
  names in `report.py` (`_LANG_NAMES`). There is **no Spanish** in the corpus.

## Known issues / tech debt (from code review — fix opportunistically)

1. **BUG (active):** `periods._write_period_summary` reads `res.get("summary", {})`,
   but `analyze.run_analysis` returns no `"summary"` key — so `period_comparison.csv`
   has empty metric columns. Fix: compute totals from the keys that exist
   (`len(res["authors"])`, `sum(res["temporal"]["citations"])`, etc.).
2. The `config.OUTPUT_DIR = …` mutate-and-restore pattern (periods.py, gui.py,
   main.py) is not thread-safe; the GUI runs the pipeline on a daemon thread.
   Prefer threading an explicit `output_dir` param through analyze/report/visualize.
   Also: `PUBMED_QUERY.rsplit('AND (')` string surgery is fragile.
3. Function-level imports in periods.py and `importlib.reload` in gui.py hide the
   dependency graph — fix the underlying cycle rather than papering over it.
4. `_filter_by_period` silently drops unparseable-year records without counting.
   Log/count them.
5. **No tests.** `demo.py` is almost a fixture — wire it into pytest with asserts
   (synthetic Hafezi pub count, period slicing, disambiguation safelist).
6. Nit: unused `import os` in periods.py. gui.py is ~1,900 lines with inline HTML.

## Conventions

- Match existing style; no new heavy dependencies (see the four-package rule).
- When editing `report.py`, `gui.py`, or `check_deps.py`, check whether the same
  change is needed in `kc_biblio` — they're kept in parity.
- Commit messages: short imperative summary line; mention which pipeline stage.
- This is a private research repo on GitHub (`markhillen/cxl-bibliometrics`).
