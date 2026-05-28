# CXL Bibliometric Analysis Pipeline

A fully self-contained Python pipeline for bibliometric analysis of
corneal cross-linking (CXL) research, using PubMed / NCBI E-utilities
and CrossRef. No Web of Science or Scopus required.

---

## Quick Start

### 1. Requirements

Python 3.10+ and four packages (numpy, matplotlib, networkx, openpyxl):

```bash
python3 -m pip install -r requirements.txt
```

If you are not using a virtual environment and pip complains about an
externally-managed environment, add `--break-system-packages`:

```bash
python3 -m pip install -r requirements.txt --break-system-packages
```

No Biopython or `requests` required — HTTP uses the standard-library
`urllib`. `pandas`, `seaborn`, and `scipy` are not used. The optional
`pyvis` package enables the interactive HTML co-authorship network; the
pipeline runs fine without it.

To verify your environment before a run:

```bash
python3 check_deps.py
```

### 2. Get an NCBI API key (free, recommended)

Register at https://www.ncbi.nlm.nih.gov/account/  
→ Settings → API Key Management  
With a key: 10 requests/sec. Without: 3 requests/sec (still works, just slower).

### 3. Run with your PMID list

You already have `pmids_expanded.txt` (2,895 PMIDs). Place it in the
same directory as the scripts and run:

```bash
python3 main.py --api-key YOUR_NCBI_KEY --pmid-file pmids_expanded.txt
```

This will:
1. Fetch all 2,895 full records from PubMed (~2–5 min)
2. Run author disambiguation
3. Enrich country from affiliations
4. Fetch citation counts from CrossRef (~25–40 min for 2,895 DOIs)
5. Run all bibliometric analyses
6. Generate 10 figures + CSV tables + Excel workbook

Results go to `outputs/cxl_biblio/`.

### 4. Skip CrossRef (faster, no citation counts)

```bash
python3 main.py --api-key YOUR_NCBI_KEY --pmid-file pmids_expanded.txt --skip-citations
```

Runs in ~3–5 minutes total.

### 5. Re-run analysis on cached data (no re-downloading)

```bash
python3 main.py --skip-fetch --skip-citations
```

---

## Outputs

| File | Contents |
|------|----------|
| `fig1_temporal_trends.png` | Annual publications + cumulative + citations over time |
| `fig2_top_journals.png` | Top 20 journals by article count |
| `fig3_top_countries.png` | Top 20 countries (publications + citations) |
| `fig4_top_authors.png` | Top 25 authors (total + first-author pubs) |
| `fig5_keywords.png` | Top 50 author keywords |
| `fig5b_mesh_terms.png` | Top 50 MeSH terms |
| `fig6_pub_types.png` | Publication type breakdown (pie) |
| `fig7_country_collab.png` | Country collaboration heatmap |
| `fig8_keyword_trends.png` | Keyword trends over time |
| `fig9_institutions.png` | Top 20 institutions |
| `fig10_author_network.png` | Author co-authorship network |
| `cxl_bibliometrics.xlsx` | All tables as formatted Excel sheets |
| `summary_stats.csv` | Key headline numbers |
| `authors_top.csv` | Top 100 authors |
| `journals_top.csv` | Top journals |
| `countries_top.csv` | Top countries |
| `keywords_top.csv` | Top 100 keywords |
| `mesh_top.csv` | Top 100 MeSH terms |
| `institutions_top.csv` | Top 50 institutions |
| `temporal.csv` | Year-by-year counts |

---

## Module Overview

```
config.py          — All settings (dates, thresholds, paths)
fetch.py           — PubMed API retrieval + XML parsing
disambiguate.py    — Author name disambiguation
geo.py             — Country extraction from affiliations
citations.py       — CrossRef citation count lookup
analyze.py         — All bibliometric calculations
visualize.py       — Chart generation (matplotlib)
report.py          — CSV + Excel output
main.py            — Orchestrator
demo.py            — Test run with 500 synthetic records
```

---

## Author Disambiguation

The pipeline uses a four-tier heuristic:

1. **ORCID** (if present in PubMed record) — definitive identity
2. **Exact last name + full forename match** — merges trivially
3. **Last name + initials + shared co-author overlap** — if two
   name variants share ≥2 co-authors, treated as same person
4. **Affiliation string similarity** — Jaccard ≥0.35 + ≥1 shared
   co-author as a tiebreaker

This handles common Asian name ambiguity reasonably well.
Tune `DISAMBIGUATION_CO_AUTHOR_THRESHOLD` in `config.py` to be
more (higher) or less (lower = 1) conservative.

**Note on h-index**: True per-author h-index requires per-paper
citation counts, which CrossRef only provides per-DOI (times cited
*of* that paper). The `h_index_estimate` column is an approximation
only — √(total_citations × 0.5). For true h-index, Scopus Author
Search or Google Scholar are needed.

---

## Changing Date Range or Query

Edit `config.py`:

```python
START_YEAR = 2001
END_YEAR   = 2025

# Or override from command line:
python3 main.py --pmid-file pmids.txt --start-year 2010 --end-year 2025
```

To re-run a search from scratch (without a PMID file), remove
`--pmid-file` and the pipeline will run `esearch` using the
`PUBMED_QUERY` in `config.py`.

---

## Cache Files

The `cache/` directory stores intermediate results so each step
can be re-run independently:

| File | Contents |
|------|----------|
| `cache/records.json` | Raw fetched records (re-use with `--skip-fetch`) |
| `cache/records_disambig.json` | After author disambiguation |
| `cache/records_cited.json` | After citation enrichment |
| `cache/citation_cache.json` | CrossRef DOI → citation count map |
| `data/analysis.json` | All computed statistics |

Delete `cache/records.json` and re-run with `--refresh` to force
a complete re-download.

---

## Troubleshooting

**"HTTP 429 Too Many Requests" from NCBI**  
Increase `REQUEST_DELAY` in `config.py` (e.g. to `0.5`) or
ensure your API key is set.

**CrossRef fetch is very slow**  
Normal — CrossRef rate-limits the polite pool to ~1 req/sec.
Use `--skip-citations` for a fast first pass, then run
`python3 citations.py` separately overnight.

**Author counts seem low**  
Lower `MIN_AUTHOR_PUBS` in `config.py` (default: 3).

**Country shows "Unknown" for many records**  
Older PubMed records often lack affiliation data. The pipeline
falls back to the journal's country of publication in those cases.
You can extend the `_COUNTRY_PATTERNS` list in `geo.py`.
