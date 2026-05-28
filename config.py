"""
CXL Bibliometric Analysis — Configuration
==========================================
Edit this file to change search parameters, date ranges, API keys, and output paths.
"""

import os
from datetime import date

# ── Project identity ──────────────────────────────────────────────────────────
PROJECT_NAME    = "CXL Bibliometrics"
PROJECT_VERSION = "2.0.0"

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
# Corneal-specific cross-linking query; avoids cartilage, dental, polymer etc.
PUBMED_QUERY = (
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
DISAMBIGUATION_CO_AUTHOR_THRESHOLD = 2
MIN_AUTHOR_PUBS = 3

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
