"""
CXL Bibliometric Analysis — Configuration
==========================================
Edit this file to change search parameters, date ranges, API keys, and output paths.
"""

import os
from datetime import date

# ── Project identity ──────────────────────────────────────────────────────────
PROJECT_NAME    = "CXL Bibliometrics"
PROJECT_VERSION = "3.0.0"
# Bump when the parsed-record schema changes; main.py refuses stale caches.
CACHE_SCHEMA    = 3

# ── API Credentials ───────────────────────────────────────────────────────────
# Get a free NCBI API key at: https://www.ncbi.nlm.nih.gov/account/
# With key: 10 requests/sec  |  Without key: 3 requests/sec
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")   # set env var or paste here

# ── Date Range ────────────────────────────────────────────────────────────────
# CXL was first reported clinically in 2003 (Wollensak et al.); 2001 captures
# any preclinical precursors indexed under corneal cross-linking.
ALL_TIME_START = 2001
END_YEAR       = min(date.today().year, 2025)  # capped at manuscript corpus year
START_YEAR     = ALL_TIME_START      # used for primary/default window

# Which date defines a record's publication year.
#   "earliest" — min(journal-issue year, online-first year); mirrors PubMed's
#                own [PDAT] filter, which accepts either date.
#   "issue"    — journal-issue year (falls back to online-first, then PubMed entry).
# Earlier versions used the PubMed *entry* date, which is not a publication date.
YEAR_RULE      = "earliest"

# ── Analysis time windows ─────────────────────────────────────────────────────
# All windows slice the same fetched dataset — no extra API calls.
# CXL literature starts 2001 so "all_time" ~= last 25yr; no need to duplicate.
ANALYSIS_PERIODS = [
    ("all_time",       ALL_TIME_START, END_YEAR),
    ("last_20yr",      END_YEAR - 19,  END_YEAR),
    ("last_15yr",      END_YEAR - 14,  END_YEAR),
    ("last_10yr",      END_YEAR - 9,   END_YEAR),
    ("last_5yr",       END_YEAR - 4,   END_YEAR),
    ("last_3yr",       END_YEAR - 2,   END_YEAR),
    ("decade_2011_20", 2011,           2020),
    ("decade_2001_10", 2001,           2010),
]

# ── PubMed Search Query ───────────────────────────────────────────────────────
# Block A (procedure signal) AND block B (corneal anchor).  There is deliberately
# no NOT block: with the corneal anchor in place, a tiab NOT list only ever
# removed genuine CXL papers (the 2001–2025 v2 query's "wound healing"[tiab]
# alone excluded 49 records, among them the Sub400 protocol paper and the
# Cochrane transepithelial-vs-epi-off review).  Off-topic records are removed by
# the logged relevance filter (relevance.py) instead, so every exclusion is
# visible in output/exclusion_log.csv.
#
# Bare "cross-linking"/"crosslinking" is admitted only alongside a CXL disease or
# agent term; on its own it floods the corpus with scaffold/biomaterial work.
# "CXL"[tiab] is safe once anchored.  The MeSH descriptor Corneal Cross-Linking
# was introduced in 2023 and adds almost nothing before then.
PUBMED_QUERY_BASE = (
    '('
    # A. procedure signal — any one
    '"corneal cross-linking"[tiab] OR "corneal crosslinking"[tiab] OR "corneal cross linking"[tiab] OR '
    '"corneal collagen cross-linking"[tiab] OR "corneal collagen crosslinking"[tiab] OR '
    '"corneal collagen cross linking"[tiab] OR '
    '"collagen cross-linking"[tiab] OR "collagen crosslinking"[tiab] OR "collagen cross linking"[tiab] OR '
    '"stromal cross-linking"[tiab] OR "stromal crosslinking"[tiab] OR '
    '"CXL"[tiab] OR "A-CXL"[tiab] OR "ACXL"[tiab] OR "PACK-CXL"[tiab] OR "KXL"[tiab] OR "C3-R"[tiab] OR '
    '"epi-off"[tiab] OR "epithelium-off"[tiab] OR '
    '"photoactivated chromophore"[tiab] OR '
    '("riboflavin"[tiab] AND ("ultraviolet"[tiab] OR "UVA"[tiab] OR "UV-A"[tiab])) OR '
    '"Corneal Cross-Linking"[MeSH Terms] OR '
    # bare cross-linking is admitted from the TITLE only, and only with a CXL
    # disease/agent term somewhere in the record
    '(("cross-linking"[ti] OR "crosslinking"[ti] OR "cross-linked"[ti] OR "crosslinked"[ti]) AND '
    '("keratoconus"[tiab] OR "keratoconic"[tiab] OR "ectasia"[tiab] OR "ectatic"[tiab] OR '
    '"keratectasia"[tiab] OR "pellucid marginal"[tiab] OR "keratitis"[tiab] OR "riboflavin"[tiab] OR '
    '"Keratoconus"[MeSH Terms]))'
    ') AND ('
    # B. corneal anchor
    '"cornea"[tiab] OR "corneal"[tiab] OR "corneas"[tiab] OR "keratoconus"[tiab] OR "keratoconic"[tiab] OR '
    '"ectasia"[tiab] OR "ectatic"[tiab] OR "keratectasia"[tiab] OR "keratitis"[tiab] OR '
    '"pellucid marginal"[tiab] OR '
    '"Cornea"[MeSH Terms] OR "Corneal Diseases"[MeSH Terms] OR "Keratoconus"[MeSH Terms]'
    ')'
)
# Note: "epi-on"/"epithelium-on" are NOT searched — PubMed drops "on" as a
# stop-word and the phrase degenerates to "epithelium", which retrieved ~340
# unrelated corneal-epithelium papers.  "UV A" degenerates to "uv" the same way.
PUBMED_QUERY = (
    f'({PUBMED_QUERY_BASE}) '
    f'AND ("{ALL_TIME_START}/01/01"[PDAT] : "{END_YEAR}/12/31"[PDAT])'
)

# Previous query (v2, used for the 2,853-record manuscript corpus of July 2026),
# kept for the audit trail and for validation.py --compare-queries.
PUBMED_QUERY_V2 = (
    '('
    '"corneal cross-linking"[tiab] OR "corneal crosslinking"[tiab] OR '
    '"corneal collagen cross-linking"[tiab] OR "corneal collagen crosslinking"[tiab] OR '
    '"collagen cross-linking"[tiab] OR "collagen crosslinking"[tiab] OR '
    '"riboflavin ultraviolet"[tiab] OR "riboflavin/UVA"[tiab] OR '
    '"KXL"[tiab] OR "C3-R"[tiab] OR "PACK-CXL"[tiab] OR '
    '"Corneal Cross-Linking"[MeSH Terms]'
    ') '
    'AND ('
    '"cornea"[tiab] OR "corneal"[tiab] OR "keratoconus"[tiab] OR '
    '"ectasia"[tiab] OR "keratitis"[tiab] OR "keratectasia"[tiab] OR '
    '"cornea"[MeSH Terms] OR "keratoconus"[MeSH Terms]'
    ') '
    'NOT ('
    '"cartilage"[tiab] OR "dental"[tiab] OR "bone"[tiab] OR '
    '"skin"[tiab] OR "aorta"[tiab] OR "artery"[tiab] OR "arterial"[tiab] OR '
    '"hydrogel"[tiab] OR "polymer"[tiab] OR "scaffold"[tiab] OR '
    '"tissue engineering"[tiab] OR "wound healing"[tiab]'
    ') '
    f'AND ("{ALL_TIME_START}/01/01"[PDAT] : "{END_YEAR}/12/31"[PDAT])'
)

# ── Fetch Settings ────────────────────────────────────────────────────────────
BATCH_SIZE        = 200
REQUEST_DELAY     = 0.15
MAX_RETRIES       = 3

# ── Author Disambiguation ─────────────────────────────────────────────────────
DISAMBIGUATION_CO_AUTHOR_THRESHOLD        = 2      # shared co-authors to merge name variants
DISAMBIGUATION_AFFIL_JACCARD              = 0.35   # affiliation-token Jaccard to merge (with ≥1 shared co-author)
DISAMBIGUATION_AFFIL_JACCARD_COMMON       = 0.55   # same, for high-collision surnames (_COMMON_SURNAMES)
DISAMBIGUATION_CO_AUTHOR_THRESHOLD_COMMON = 2      # shared co-authors required with the Jaccard rule for common surnames
MIN_AUTHOR_PUBS = 3

# ── Institution attribution (main table; all variants go to output/sdc/) ──────
# counting: "primary" = the first author's first-listed resolvable affiliation
#           (one institution per record, counts are mutually exclusive);
#           "whole"   = every institution the first author lists, 1 each
#           (the rule behind the v16 manuscript's Table 3; counts overlap);
#           "fractional" = every institution, 1/k each.
# level:    "canonical" | "parent" | "cluster"  (data/institution_aliases.csv)
# first_author_only: True  = credit only the first author's institution
#                    False = credit every institution named by any author, which
#                    is what institutional rankings normally report. First-author
#                    -only systematically under-credits groups whose people
#                    publish as senior or middle authors, so the manuscript
#                    reports all-author counting and keeps first-author-only as
#                    the sensitivity analysis. Both tables are always written.
INSTITUTION_FIRST_AUTHOR_ONLY = False
INSTITUTION_COUNTING = "whole"
INSTITUTION_LEVEL    = "canonical"

# ── Citation Enrichment ───────────────────────────────────────────────────────
FETCH_CITATIONS      = True
CITATION_BATCH_DELAY = 0.5

# ── Co-occurrence / Network ───────────────────────────────────────────────────
MIN_KEYWORD_FREQ  = 5
MIN_COOCCURRENCE  = 3
TOP_N_AUTHORS     = 30
TOP_N_COUNTRIES   = 20
TOP_N_JOURNALS    = 20
TOP_N_KEYWORDS    = 50
TOP_N_INSTITUTIONS = 20

# ── Paths ─────────────────────────────────────────────────────────────────────
import pathlib as _pl
_HERE      = _pl.Path(__file__).resolve().parent

BASE_DIR   = str(_HERE)
DATA_DIR   = str(_HERE / "data")
CACHE_DIR  = str(_HERE / "cache")
OUTPUT_DIR = str(_HERE / "output")

for _d in [DATA_DIR, CACHE_DIR, OUTPUT_DIR]:
    _pl.Path(_d).mkdir(parents=True, exist_ok=True)

# ── Figure format ─────────────────────────────────────────────────────────────
# "pdf" — vector, best for journal submission
# "svg" — vector, editable in Illustrator / Inkscape
# "png" — raster (300 dpi); avoid for publication figures
FIGURE_FORMAT = "pdf"
FIG_MAX_WIDTH_IN = 7.0            # journal full-page width; _save() warns beyond this
CITATION_SOURCE_LABEL = "OpenAlex"  # axis label for citation panels (set by main.py per run mode)
PER_CAPITA_MIN_PUBS = 20          # Figure 2D and SDC per-capita table: minimum first-author publications
KEYWORD_TREND_MIN_RECORDS = 10    # Figure 3A: first year with at least this many keyword-bearing records
CITATION_FILL_CROSSREF = False   # True → records without an OpenAlex match take their CrossRef count (source "crossref")
