"""
CXL Bibliometric Analysis — Configuration
==========================================
Edit this file to change search parameters, date ranges, API keys, and output paths.
"""

import os

# ── API Credentials ──────────────────────────────────────────────────────────
# Get a free NCBI API key at: https://www.ncbi.nlm.nih.gov/account/
# With key: 10 requests/sec  |  Without key: 3 requests/sec
NCBI_API_KEY = os.environ.get("NCBI_API_KEY", "")   # set env var or paste here

# ── Date Range ────────────────────────────────────────────────────────────────
START_YEAR = 2001
END_YEAR   = 2025   # inclusive

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
    f'AND ("{START_YEAR}/01/01"[PDAT] : "{END_YEAR}/12/31"[PDAT])'
)

# ── Fetch Settings ────────────────────────────────────────────────────────────
BATCH_SIZE        = 200    # records per API request (max 10000, but 200 is stable)
REQUEST_DELAY     = 0.15   # seconds between requests (0.1 with key, 0.34 without)
MAX_RETRIES       = 3

# ── Author Disambiguation ─────────────────────────────────────────────────────
# Minimum co-author overlap to merge two "same-name" author variants
DISAMBIGUATION_CO_AUTHOR_THRESHOLD = 2
# Minimum publications for author to appear in rankings
MIN_AUTHOR_PUBS = 3

# ── Citation Enrichment ───────────────────────────────────────────────────────
# Uses CrossRef free API to fetch citation counts by DOI — can be slow for large sets
FETCH_CITATIONS      = True
CITATION_BATCH_DELAY = 0.5   # be polite to CrossRef

# ── Co-occurrence / Network ───────────────────────────────────────────────────
MIN_KEYWORD_FREQ     = 5     # minimum occurrences to include in keyword network
MIN_COOCCURRENCE     = 3     # minimum co-occurrence for an edge
TOP_N_AUTHORS        = 30    # for network graphs
TOP_N_COUNTRIES      = 20
TOP_N_JOURNALS       = 20
TOP_N_KEYWORDS       = 50

# ── Paths — all relative to wherever this config.py lives ────────────────────
import pathlib as _pl
_HERE      = _pl.Path(__file__).resolve().parent   # folder containing config.py

BASE_DIR   = str(_HERE)
DATA_DIR   = str(_HERE / "data")
CACHE_DIR  = str(_HERE / "cache")
OUTPUT_DIR = str(_HERE / "outputs")

# Create dirs
for _d in [DATA_DIR, CACHE_DIR, OUTPUT_DIR]:
    _pl.Path(_d).mkdir(parents=True, exist_ok=True)

# ── Figure format ─────────────────────────────────────────────────────────────
# "pdf" — vector, best for journal submission
# "svg" — vector, editable in Illustrator / Inkscape
# "png" — raster (300 dpi); avoid for publication figures
FIGURE_FORMAT = "pdf"
