"""
keywords.py — author-keyword normalisation
==========================================

Author keywords in PubMed are free text: the same concept arrives as
"Accelerated CXL", "accelerated cross‑linking" (non-breaking hyphen),
"accelerated crosslinking", "A-CXL", "kératocône", "Keratoconus" …  Before
counting, every keyword passes through:

  1. Unicode NFKC, case folding, all dash variants → "-", accents stripped,
     whitespace collapsed, trailing punctuation removed
  2. rule-based family normalisation (cross-link*, transepithelial/epi-on,
     epi-off, UVA, A-CXL, PACK-CXL, keratoconus in any language)
  3. light singularisation
  4. exact lookup in data/keyword_synonyms.csv (variant → canonical)
  5. family fallbacks for anything still carrying a recognisable stem

The synonym table is data, published with the SDC.  ``coverage_by_year`` gives
the denominator every temporal keyword statement needs: the share of records
that carry any author keyword at all (0% before 2006, ~65% in 2021–2025).
"""

from __future__ import annotations

import csv
import pathlib
import re
import sys
import unicodedata

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import config

SYN_PATH = pathlib.Path(config.DATA_DIR) / "keyword_synonyms.csv"

CANON_CXL = "corneal cross-linking (CXL)"
CANON_ACCEL = "accelerated CXL"
CANON_EPI_ON = "transepithelial (epi-on) CXL"
CANON_EPI_OFF = "epi-off CXL"
CANON_PACK = "PACK-CXL"
CANON_KC = "keratoconus"
CANON_UVA = "ultraviolet-A (UVA)"

# The canonical search-term concepts excluded from thematic charts by default
SEARCH_TERM_CANONICALS = {CANON_CXL}

_DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−­﹣－"), "-")

_syn: dict[str, str] | None = None


def load_synonyms(path: pathlib.Path | None = None) -> dict[str, str]:
    global _syn
    if _syn is not None and path is None:
        return _syn
    path = path or SYN_PATH
    d: dict[str, str] = {}
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                v = _basic(row.get("variant", ""))
                c = (row.get("canonical") or "").strip()
                if v and c:
                    d[v] = c
    if path == SYN_PATH:
        _syn = d
    return d


def reset() -> None:
    global _syn
    _syn = None


def _basic(s: str) -> str:
    s = unicodedata.normalize("NFKC", s or "")
    s = s.translate(_DASHES)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.casefold()
    s = re.sub(r"\s+", " ", s).strip()
    s = s.strip(" .,;:!?\"'")
    s = re.sub(r"\s*-\s*", "-", s)          # "cross - linking" → "cross-linking"
    s = re.sub(r"\s*/\s*", "/", s)
    return s


_FAMILY_PRE = [
    (re.compile(r"\bcross[\s-]?link(ing|ed|s)?\b"), "cross-linking"),
    (re.compile(r"\bcrosslink(ing|ed|s)?\b"), "cross-linking"),
    (re.compile(r"\btrans[\s-]?epithelial\b"), "transepithelial"),
    (re.compile(r"\bepi(?:thelium|thelial)?[\s-]?on\b"), "epi-on"),
    (re.compile(r"\bepi(?:thelium|thelial)?[\s-]?off\b"), "epi-off"),
    (re.compile(r"\b(?:ultraviolet|uv)[\s-]?a\b"), "uva"),
    (re.compile(r"\bultra[\s-]?violet\b"), "ultraviolet"),
    (re.compile(r"\ba[\s-]?cxl\b"), "accelerated cxl"),
    (re.compile(r"\bpack[\s-]?cxl\b"), "pack-cxl"),
    (re.compile(r"\bkerato?c[oô]ne?\b|\bqueratocono\b|\bcheratocono\b|\bkeratokonus\b"), "keratoconus"),
    (re.compile(r"\bcornee\b|\bcornea\b"), "cornea"),
    (re.compile(r"\bp(?:a)?ediatric\b"), "paediatric"),
    (re.compile(r"\((cxl|kc|uva|prk|oct)\)"), r"\1"),
]

_SINGULAR_EXCEPTIONS = {"lens", "keratoconus", "sclera", "cornea", "stroma", "diabetes", "analysis",
                        "genesis", "series", "hysteresis", "mitosis", "apoptosis", "ptosis", "uveitis",
                        "keratitis", "ectasis", "sis", "iris", "us", "is", "as", "os"}


def _singular(term: str) -> str:
    toks = term.split(" ")
    if not toks:
        return term
    last = toks[-1]
    if last in _SINGULAR_EXCEPTIONS or len(last) < 5 or last.endswith(("ss", "us", "is", "sis", "itis", "ics")):
        return term
    if last.endswith("ies"):
        toks[-1] = last[:-3] + "y"
    elif last.endswith("ses") or last.endswith("xes") or last.endswith("ches"):
        toks[-1] = last[:-2]
    elif last.endswith("s"):
        toks[-1] = last[:-1]
    return " ".join(toks)


_FAMILY_POST = [
    (re.compile(r"^(?:corneal )?(?:collagen )?cross-linking(?: \(?cxl\)?)?$"), CANON_CXL),
    (re.compile(r"^(?:corneal )?(?:collagen )?(?:riboflavin[/ ]uva |uva[/ ]riboflavin )?cross-linking(?: treatment| therapy)?$"), CANON_CXL),
    (re.compile(r"^(?:corneal )?cxl$"), CANON_CXL),
    (re.compile(r"^(?:corneal )?collagen cross-linking with riboflavin$"), CANON_CXL),
    (re.compile(r"\baccelerated\b"), CANON_ACCEL),
    (re.compile(r"\b(?:transepithelial|epi-on|iontophore(?:sis|tic))\b"), CANON_EPI_ON),
    (re.compile(r"\bepi-off\b|^standard (?:cxl|cross-linking)$|^dresden protocol$"), CANON_EPI_OFF),
    (re.compile(r"\bpack-cxl\b|^photoactivated chromophore"), CANON_PACK),
    (re.compile(r"^(?:progressive |early |advanced |subclinical |forme fruste |unilateral |bilateral |mild |moderate |severe )?keratoconus$"), CANON_KC),
    (re.compile(r"^p(?:a)?ediatric keratoconus$|^childhood keratoconus$|^keratoconus in child(?:ren)?$"), "paediatric keratoconus"),
    (re.compile(r"^uva$|^uva (?:light|irradiation|radiation)$|^ultraviolet$|^ultraviolet (?:light|irradiation|radiation)$"), CANON_UVA),
]


def normalize(raw: str) -> str | None:
    """Raw author keyword → canonical term (or None for empty input)."""
    s = _basic(raw)
    if not s:
        return None
    for rx, rep in _FAMILY_PRE:
        s = rx.sub(rep, s)
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\b(\w+)( \1\b)+", r"\1", s)      # "uva uva" → "uva"
    s = _singular(s)
    syn = load_synonyms()
    if s in syn:
        return syn[s]
    for rx, canon in _FAMILY_POST:
        if rx.search(s):
            return canon
    return s


def coverage_by_year(records: list[dict]) -> list[dict]:
    by: dict[int, list[int]] = {}
    for rec in records:
        try:
            y = int(rec.get("year") or 0)
        except ValueError:
            continue
        if not y:
            continue
        n, k = by.get(y, [0, 0])
        by[y] = [n + 1, k + (1 if rec.get("keywords") else 0)]
    rows = [{"year": y, "n_records": n, "n_with_author_keywords": k,
             "pct": round(100 * k / n, 1) if n else 0.0} for y, (n, k) in sorted(by.items())]
    return rows


def coverage_overall(records: list[dict]) -> dict:
    n = len(records)
    k = sum(1 for r in records if r.get("keywords"))
    return {"n_records": n, "n_with_author_keywords": k, "pct": round(100 * k / n, 1) if n else 0.0}


def record_terms(rec: dict, source: str = "author") -> set[str]:
    """Normalised, de-duplicated terms of one record from the chosen source."""
    raw: list[str] = []
    if source in ("author", "both"):
        raw += rec.get("keywords", []) or []
    if source in ("mesh", "both"):
        raw += rec.get("mesh", []) or []
    out = set()
    for k in raw:
        t = normalize(k) if source != "mesh" else _basic(k)
        if t:
            out.add(t)
    return out


def trends(records: list[dict], terms: list[str], source: str = "author") -> dict:
    """Per-year share (%) of keyword-bearing records that carry each term."""
    cov = {r["year"]: r for r in coverage_by_year(records)}
    counts: dict[str, dict[int, int]] = {t: {} for t in terms}
    for rec in records:
        try:
            y = int(rec.get("year") or 0)
        except ValueError:
            continue
        if not y or not rec.get("keywords"):
            continue
        ts = record_terms(rec, source)
        for t in terms:
            if t in ts:
                counts[t][y] = counts[t].get(y, 0) + 1
    years = sorted(cov)
    return {
        "years": years,
        "denominator": [cov[y]["n_with_author_keywords"] for y in years],
        "n_records": [cov[y]["n_records"] for y in years],
        "counts": {t: [counts[t].get(y, 0) for y in years] for t in terms},
        "share_pct": {t: [round(100 * counts[t].get(y, 0) / cov[y]["n_with_author_keywords"], 1)
                          if cov[y]["n_with_author_keywords"] else None for y in years] for t in terms},
    }


def write_synonyms_export(path: pathlib.Path) -> None:
    path.write_bytes(SYN_PATH.read_bytes())
