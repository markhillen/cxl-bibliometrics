# CXL Bibliometric Analysis Pipeline

A self-contained Python pipeline for bibliometric analysis of the
corneal cross-linking (CXL) research literature. Pulls data from
PubMed for the corpus and OpenAlex for citations, countries, and institutions (with CrossRef retained as a cross-check) — no Web of Science or Scopus subscription required.

---

## Quick start (no technical knowledge needed)

**Double-click `Start.command`** — it sets up everything (a private Python
environment and the required packages, about a minute the first time) and opens
the app in your browser. See `QUICKSTART.txt` for troubleshooting.

**First run:** a fresh download does *not* include the dataset — it ships the
PubMed ID list instead. On first use, open the app and click **Run Analysis**
(PMID-file mode, with `pmids_expanded.txt`) to build the dataset. This takes a
few minutes; an NCBI API key (below) just makes it faster. After that, results
load instantly from the local cache.

---

## Requirements

**Python 3.10 or later.** Check your version:

```bash
python3 --version
```

Four packages are required (`numpy`, `matplotlib`, `networkx`, `openpyxl`):

```bash
python3 -m pip install -r requirements.txt
```

On a system-managed Python (macOS Homebrew, Debian/Ubuntu) pip may refuse
without a virtualenv. Add `--break-system-packages` to override:

```bash
python3 -m pip install -r requirements.txt --break-system-packages
```

`requests`, `pandas`, `seaborn`, and `scipy` are **not** used — HTTP uses
the standard-library `urllib`. The optional `pyvis` package enables the
interactive HTML co-authorship network; the pipeline runs fine without it:

```bash
# optional
python3 -m pip install pyvis --break-system-packages
```

Verify your environment before running:

```bash
python3 check_deps.py
```

---

## NCBI API Key

Free to register at <https://www.ncbi.nlm.nih.gov/account/> → Settings →
API Key Management. With a key: 10 req/s. Without: 3 req/s (still works,
just slower). Pass it via `--api-key` or set the `NCBI_API_KEY` environment
variable.

---

## Data Sources

The pipeline supports three ways to supply records:

### Option A — PMID list file (recommended for reproducibility)

Export PMIDs from a PubMed search and save them one per line, then:

```bash
python3 main.py --api-key YOUR_KEY --pmid-file pmids_expanded.txt
```

### Option B — PubMed query (fetch by search term)

```bash
python3 main.py --api-key YOUR_KEY
```

The query is defined in `config.py` under `PUBMED_QUERY`. Edit it there,
or use the GUI's PubMed Query mode to test alternatives interactively.

### Option C — Cached records only (fastest, no network)

> Note: a fresh download has no cache yet — run Option A once first.

Once records have been downloaded, skip re-fetching entirely:

```bash
python3 main.py --skip-fetch --skip-citations
```

---

## Running the Pipeline

### Launch the web GUI

```bash
python3 gui.py
```

Opens a local app in your browser (date-range sliders, results tables, figures,
and downloadable CSV/Excel). Non-technical users can just double-click
`Start.command` instead (see Quick start).



### Full run (fetch + citations + analysis, ~30–50 min)

```bash
python3 main.py --api-key YOUR_KEY --pmid-file pmids_expanded.txt
```

Steps performed:
1. Fetch full records from PubMed via E-utilities (~2–5 min)
2. Author disambiguation
3. Country extraction from affiliations
4. Citation counts from CrossRef (~25–40 min)
5. Bibliometric analysis across all time windows
6. Figures (PDF) + CSV tables + Excel workbook per period

### OpenAlex hybrid enrichment (recommended)

By default the pipeline can also use **OpenAlex** — a free, CC0-licensed index
of works, authors, institutions, and citations — instead of CrossRef. OpenAlex
resolves author affiliations to ROR institution IDs and clean country codes
(fixing affiliation-string errors) and supplies citation counts, all keyed to
our records by DOI/PMID.

```bash
# 1. fetch the corpus from PubMed (uses the included PMID list)
python3 main.py --api-key YOUR_KEY --pmid-file pmids_expanded.txt --skip-citations
# 2. enrich with OpenAlex (country + institution + citations)
python3 openalex_enrich.py
# 3. regenerate the analysis in hybrid mode
python3 main.py --skip-fetch --skip-citations --use-openalex
```

`openalex_compare.py` prints a side-by-side of OpenAlex vs the current numbers.
CrossRef counts are retained in parallel as a cross-check. OpenAlex requires a
free API key as of 2026 (single-record lookups by DOI/PMID remain free).

### Skip CrossRef (~3–5 min total)

Useful for a fast first pass; citation columns will be zero or empty.

```bash
python3 main.py --api-key YOUR_KEY --pmid-file pmids_expanded.txt --skip-citations
```

### Re-run analysis on cached data (no API calls, ~30 s)

```bash
python3 main.py --skip-fetch --skip-citations
```

### Single time window only

```bash
python3 main.py --skip-fetch --skip-citations --period last_5yr
```

### Force a complete re-download

```bash
python3 main.py --api-key YOUR_KEY --pmid-file pmids_expanded.txt --refresh
```

---

## GUI (browser-based interface)

```bash
python3 gui.py
```

Opens at <http://localhost:7432>. Lets you choose a data source, date
range, and options, then run the pipeline and browse results, figures,
and downloads — all without the command line.

---

## Time Windows

The pipeline analyses the same fetched records across eight overlapping
windows in a single run:

| Label            | Years       | Records (approx.) |
|------------------|-------------|-------------------|
| `all_time`       | 2001–present | ~2,850           |
| `last_20yr`      | 2006–present | ~2,840           |
| `last_15yr`      | 2011–present | ~2,650           |
| `last_10yr`      | 2016–present | ~1,900           |
| `last_5yr`       | 2021–present | ~960             |
| `last_3yr`       | 2023–present | ~540             |
| `decade_2011_20` | 2011–2020    | ~1,690           |
| `decade_2001_10` | 2001–2010    | ~200             |

---

## Output Structure

All output is written to `output/` (overridable via `CXL_OUTPUT_DIR`).
Each time window gets its own subdirectory:

```
output/
├── all_time/
│   ├── fig1_temporal_trends.pdf       annual output + cumulative + citations
│   ├── fig2_top_journals.pdf          top 20 journals by article count
│   ├── fig3_top_countries.pdf         top 20 countries (pubs + citations)
│   ├── fig4_top_authors.pdf           top authors (total + first-author pubs)
│   ├── fig5_author_keywords.pdf       top 50 author keywords
│   ├── fig5_mesh_terms.pdf            top 50 MeSH terms
│   ├── fig6_pub_types.pdf             publication type breakdown
│   ├── fig7_country_collab.pdf        country collaboration heatmap
│   ├── fig8_keyword_trends.pdf        keyword trends over time
│   ├── fig9_institutions.pdf          top 20 institutions (first-author)
│   ├── fig10_author_network.pdf       author co-authorship network
│   ├── author_network_interactive.html  (requires pyvis)
│   ├── cxl_bibliometrics.xlsx         all tables as formatted Excel sheets
│   ├── summary_stats.csv
│   ├── temporal.csv                   year-by-year counts
│   ├── authors_top.csv                top 100 authors
│   ├── journals_top.csv
│   ├── countries_top.csv              includes pubs_per_million
│   ├── keywords_top.csv               top 100 keywords
│   ├── mesh_top.csv                   top 100 MeSH terms
│   ├── institutions_top.csv           top 50 institutions
│   ├── languages.csv
│   ├── pub_types.csv
│   └── analysis.json                  all computed statistics (used by GUI)
├── last_20yr/                         same structure
├── last_15yr/
├── last_10yr/
├── last_5yr/
├── last_3yr/
├── decade_2011_20/
├── decade_2001_10/
└── period_comparison.csv              headline metrics across all windows
```

**Figure format:** the CLI produces PDF (vector, publication-ready) and SVG.
The GUI produces PNG for inline display. Pass `--skip-viz` to skip figures
entirely and generate only the data files.

---

## Cache Files

Intermediate results are stored in `cache/` so each step can be re-run
independently without repeating slow network operations:

| File | Contents |
|------|----------|
| `cache/records.json` | Raw PubMed records (reused by `--skip-fetch`) |
| `cache/records_disambig.json` | After author disambiguation |
| `cache/records_cited.json` | After citation enrichment |
| `cache/citation_cache.json` | CrossRef DOI → citation count map |

Delete `cache/records.json` and add `--refresh` to force a full re-download.

---

## Author Disambiguation

Author identity is resolved by a four-tier heuristic:

1. **ORCID** — definitive identity, merged unconditionally
2. **Exact last name + full forename** — merges trivially identical entries
3. **Last name + initials + shared co-author overlap** — ≥2 shared co-authors
   required to merge initials-only variants
4. **Affiliation string similarity** — Jaccard ≥0.35 + ≥1 shared co-author
   as a tiebreaker

Tune `DISAMBIGUATION_CO_AUTHOR_THRESHOLD` in `config.py` (default: 2).

**Note on h-index:** The `h_index_estimate` column is an approximation
(√(total_citations × 0.5)) — CrossRef provides per-paper citation counts
but not sorted per-author lists. For true h-index use Scopus or Google Scholar.

---

## Module Overview

```
config.py        all settings: dates, query, thresholds, paths
fetch.py         PubMed E-utilities retrieval + XML parsing
disambiguate.py  author name disambiguation
geo.py           country extraction from affiliation strings
citations.py     CrossRef citation count lookup
analyze.py       all bibliometric calculations
visualize.py     figure generation (matplotlib)
report.py        CSV + Excel output
periods.py       slices records into time windows, runs pipeline per window
main.py          CLI orchestrator
gui.py           local web server + browser GUI
check_deps.py    dependency checker (run before first use)
demo.py          smoke test with 500 synthetic records (no network needed)
```

---

## Troubleshooting

**`HTTP 429 Too Many Requests` from NCBI**
Increase `REQUEST_DELAY` in `config.py` (e.g. `0.5`) or ensure your
API key is set correctly.

**CrossRef enrichment is very slow**
Expected — CrossRef rate-limits the polite pool to ~1 req/s. Use
`--skip-citations` for a fast first pass, then run `python3 citations.py`
separately to fill in citation counts overnight.

**Figures tab empty in GUI after a CLI run**
The GUI displays SVG files (produced by the CLI alongside PDF). If
`output/<period>/` contains only PDFs and no SVGs, re-run the pipeline.

**Author counts seem low**
Lower `MIN_AUTHOR_PUBS` in `config.py` (default: 3).

**Many records show country "Unknown"**
Older PubMed records often lack affiliation data. Extend the
`_COUNTRY_PATTERNS` list in `geo.py` to add additional patterns.

**`ModuleNotFoundError` at startup**
Run `python3 check_deps.py` for a precise diagnosis and the exact
install command needed.
