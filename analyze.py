"""
analyze.py — Bibliometric calculations
=======================================
Computes all summary statistics from enriched records:
  - Temporal trends
  - Author rankings (publications + estimated h-index)
  - Journal rankings
  - Country rankings
  - Keyword / MeSH co-occurrence
  - Collaboration networks (author, country, institution)
"""

import collections
import itertools
import re
import math
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import config
from geo import extract_country

# ─────────────────────────────────────────────────────────────────────────────
# 1. Temporal trends
# ─────────────────────────────────────────────────────────────────────────────

def temporal_trends(records: list[dict]) -> dict:
    """Publications per year, cumulative, and moving average."""
    by_year: dict[int, int] = collections.Counter()
    cite_by_year: dict[int, int] = collections.defaultdict(int)
    for rec in records:
        try:
            y = int(rec.get("year", 0))
        except (ValueError, TypeError):
            continue
        if config.START_YEAR <= y <= config.END_YEAR:
            by_year[y] += 1
            cc = rec.get("citation_count") or 0
            cite_by_year[y] += cc

    years = sorted(by_year.keys())
    counts = [by_year[y] for y in years]
    cumulative = list(itertools.accumulate(counts))
    citations = [cite_by_year[y] for y in years]

    # 3-year moving average
    def moving_avg(vals, window=3):
        out = []
        for i in range(len(vals)):
            lo = max(0, i - window // 2)
            hi = min(len(vals), i + window // 2 + 1)
            out.append(sum(vals[lo:hi]) / (hi - lo))
        return out

    return {
        "years":       years,
        "counts":      counts,
        "cumulative":  cumulative,
        "moving_avg":  moving_avg(counts),
        "citations":   citations,
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Author analysis
# ─────────────────────────────────────────────────────────────────────────────

def author_stats(records: list[dict]) -> list[dict]:
    """
    Returns list of author dicts sorted by publication count desc.
    Fields: author_id, pub_count, first_author_count, last_author_count,
            citation_total, h_index_est, years_active, journals, affiliations_sample
    """
    # Per-author aggregation
    pubs:       dict[str, list[dict]] = collections.defaultdict(list)
    first_auth: dict[str, int]        = collections.Counter()
    last_auth:  dict[str, int]        = collections.Counter()
    citations:  dict[str, int]        = collections.defaultdict(int)
    affils_sample: dict[str, list]    = collections.defaultdict(list)
    journals_per_auth: dict[str, set] = collections.defaultdict(set)
    years_per_auth: dict[str, set]    = collections.defaultdict(set)

    for rec in records:
        cc = rec.get("citation_count") or 0
        jrnl = rec.get("journal_abbr") or rec.get("journal", "")
        try:
            yr = int(rec.get("year", 0))
        except (ValueError, TypeError):
            yr = 0

        authors = rec.get("authors", [])
        # Filter out collective/anonymous entries for position calculation.
        # Build an index by object id so last-author detection is O(1) and
        # immune to duplicate dicts (named.index() would return the first match).
        named = [a for a in authors if a.get("author_id") and a["author_id"] != "__collective__"]
        n_named = len(named)
        named_last_id = id(named[-1]) if named else None
        for pos, a in enumerate(authors):
            aid = a.get("author_id")
            if not aid or aid == "__collective__":
                continue
            pubs[aid].append(rec)
            citations[aid] += cc
            journals_per_auth[aid].add(jrnl)
            if yr:
                years_per_auth[aid].add(yr)
            if pos == 0:
                first_auth[aid] += 1
            # Last author: final named position (senior/PI convention).
            # Only meaningful for multi-author papers (≥2 named authors).
            if n_named >= 2 and id(a) == named_last_id:
                last_auth[aid] += 1
            if a.get("affils") and len(affils_sample[aid]) < 3:
                affils_sample[aid].extend(a["affils"][:2])

    # Estimate h-index from available citation counts
    # (real h-index needs per-paper citations, not author totals)
    # We estimate: h ≈ √(total_citations / pub_count) × correction
    def est_h(total_cites, n_pubs):
        if n_pubs == 0 or total_cites is None:
            return 0
        return min(round(math.sqrt(total_cites * 0.5)), n_pubs)

    rows = []
    for aid, rec_list in pubs.items():
        n = len(rec_list)
        if n < config.MIN_AUTHOR_PUBS:
            continue
        tc = citations[aid]
        yrs = sorted(years_per_auth[aid])
        rows.append({
            "author_id":          aid,
            "pub_count":          n,
            "first_author_count": first_auth[aid],
            "last_author_count":  last_auth[aid],
            "citation_total":     tc,
            "h_index_est":        est_h(tc, n),
            "year_first":         yrs[0]  if yrs else None,
            "year_last":          yrs[-1] if yrs else None,
            "years_active":       len(yrs),
            "journal_count":      len(journals_per_auth[aid]),
            "affils_sample":      list(dict.fromkeys(affils_sample[aid]))[:3],
        })

    rows.sort(key=lambda x: x["pub_count"], reverse=True)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 3. Journal analysis
# ─────────────────────────────────────────────────────────────────────────────

def journal_stats(records: list[dict]) -> list[dict]:
    counter: dict[str, dict] = {}
    for rec in records:
        jname = rec.get("journal") or "Unknown"
        jabbr = rec.get("journal_abbr") or jname
        cc = rec.get("citation_count") or 0
        if jname not in counter:
            counter[jname] = {"journal": jname, "abbr": jabbr,
                               "count": 0, "citations": 0}
        counter[jname]["count"] += 1
        counter[jname]["citations"] += cc

    rows = sorted(counter.values(), key=lambda x: x["count"], reverse=True)
    total = len(records)
    for r in rows:
        r["percentage"] = round(r["count"] / total * 100, 2)
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# 4. Country analysis
# ─────────────────────────────────────────────────────────────────────────────

def country_stats(records: list[dict]) -> list[dict]:
    """Publication and citation counts per country (first author).

    Per-capita metrics use 2024 UN population estimates (millions).
    Countries absent from the lookup table receive pubs_per_million = None.
    """
    # 2024 UN population estimates (millions), covering all countries likely
    # to appear in the CXL literature.
    _POP_MILLIONS: dict[str, float] = {
        "Australia":       26.5,
        "Austria":          9.1,
        "Belgium":         11.7,
        "Brazil":         215.3,
        "Canada":          38.8,
        "China":         1412.0,
        "Czech Republic":  10.9,
        "Denmark":          5.9,
        "Egypt":          107.0,
        "Finland":          5.6,
        "France":          68.4,
        "Germany":         84.4,
        "Greece":          10.4,
        "Hungary":          9.7,
        "India":         1441.0,
        "Iran":            89.2,
        "Israel":           9.8,
        "Italy":           59.0,
        "Japan":          123.3,
        "Jordan":          10.3,
        "Lebanon":          5.5,
        "Netherlands":     17.9,
        "New Zealand":      5.1,
        "Norway":           5.5,
        "Poland":          41.0,
        "Portugal":        10.3,
        "Romania":         19.0,
        "Saudi Arabia":    36.4,
        "Singapore":        6.0,
        "South Korea":     51.7,
        "Spain":           47.4,
        "Sweden":          10.5,
        "Switzerland":      8.8,
        "Taiwan":          23.6,
        "Turkey":          85.3,
        "Ukraine":         43.5,
        "United Arab Emirates": 9.8,
        "United Kingdom":  67.7,
        "United States":  335.9,
    }

    counter: dict[str, dict] = {}
    for rec in records:
        c = rec.get("country", "Unknown")
        cc = rec.get("citation_count") or 0
        if c not in counter:
            counter[c] = {"country": c, "count": 0, "citations": 0}
        counter[c]["count"] += 1
        counter[c]["citations"] += cc

    rows = sorted(counter.values(), key=lambda x: x["count"], reverse=True)
    total = len(records)
    for r in rows:
        r["percentage"] = round(r["count"] / total * 100, 2)
        pop = _POP_MILLIONS.get(r["country"])
        if pop:
            r["pubs_per_million"]   = round(r["count"]   / pop, 2)
            r["cites_per_million"]  = round(r["citations"] / pop, 1)
        else:
            r["pubs_per_million"]  = None
            r["cites_per_million"] = None
    return rows


def country_collab_network(records: list[dict]) -> dict:
    """
    Country-level collaboration network.
    Edge weight = number of papers with authors from both countries.
    """
    node_counts: dict[str, int] = collections.Counter()
    edge_weights: dict[tuple, int] = collections.Counter()

    for rec in records:
        countries_in_paper: set[str] = set()
        for a in rec.get("authors", []):
            # Prefer OpenAlex/ROR country when the hybrid overlay supplied it;
            # fall back to affiliation-string parsing otherwise.
            c = a.get("oa_country_name")
            if not c:
                affils = a.get("affils", [])
                c = extract_country(affils) if affils else "Unknown"
            if c and c != "Unknown":
                countries_in_paper.add(c)
        for c in countries_in_paper:
            node_counts[c] += 1
        for c1, c2 in itertools.combinations(sorted(countries_in_paper), 2):
            edge_weights[(c1, c2)] += 1

    return {
        "nodes": dict(node_counts),
        "edges": {f"{k[0]}|{k[1]}": v for k, v in edge_weights.items()},
    }


# ─────────────────────────────────────────────────────────────────────────────
# 5. Keyword / MeSH co-occurrence
# ─────────────────────────────────────────────────────────────────────────────

# ── Keyword synonym map ───────────────────────────────────────────────────────
# All variants on the left collapse to the canonical term on the right.
# Applied BEFORE counting, so merged terms appear as a single entry.
_KW_SYNONYMS: dict[str, str] = {
    # ── CXL procedure name variants ──────────────────────────────────────────
    # These are all the same procedure — merge into one canonical term so the
    # keyword chart reflects clinical themes, not indexing inconsistency.
    "corneal cross-linking":                    "corneal cross-linking (CXL)",
    "corneal crosslinking":                     "corneal cross-linking (CXL)",
    "corneal collagen cross-linking":           "corneal cross-linking (CXL)",
    "corneal collagen crosslinking":            "corneal cross-linking (CXL)",
    "collagen cross-linking":                   "corneal cross-linking (CXL)",
    "collagen crosslinking":                    "corneal cross-linking (CXL)",
    "cross-linking":                            "corneal cross-linking (CXL)",
    "crosslinking":                             "corneal cross-linking (CXL)",
    "cxl":                                      "corneal cross-linking (CXL)",
    "corneal collagen cxl":                     "corneal cross-linking (CXL)",
    "uva/riboflavin cross-linking":             "corneal cross-linking (CXL)",
    "uva-riboflavin cross-linking":             "corneal cross-linking (CXL)",
    "riboflavin/uva cross-linking":             "corneal cross-linking (CXL)",
    "riboflavin/ultraviolet-a cross-linking":   "corneal cross-linking (CXL)",
    "riboflavin uv-a corneal cross-linking":    "corneal cross-linking (CXL)",
    "corneal collagen cross linking":           "corneal cross-linking (CXL)",
    "cross linking":                            "corneal cross-linking (CXL)",
    "kxl":                                      "corneal cross-linking (CXL)",

    # ── Accelerated CXL variants ─────────────────────────────────────────────
    "accelerated cxl":                          "accelerated CXL",
    "accelerated corneal cross-linking":        "accelerated CXL",
    "accelerated corneal crosslinking":         "accelerated CXL",
    "accelerated collagen cross-linking":       "accelerated CXL",
    "a-cxl":                                    "accelerated CXL",
    "acxl":                                     "accelerated CXL",

    # ── Epithelium-on/off variants ────────────────────────────────────────────
    "epithelium-off cxl":                       "epi-off CXL",
    "epi-off cxl":                              "epi-off CXL",
    "epithelium off cxl":                       "epi-off CXL",
    "standard cxl":                             "epi-off CXL",
    "dresden protocol":                         "epi-off CXL",
    "transepithelial cxl":                      "epi-on CXL (transepithelial)",
    "epithelium-on cxl":                        "epi-on CXL (transepithelial)",
    "epi-on cxl":                               "epi-on CXL (transepithelial)",
    "trans-epithelial cxl":                     "epi-on CXL (transepithelial)",
    "iontophoresis cxl":                        "epi-on CXL (transepithelial)",

    # ── PACK-CXL variants ────────────────────────────────────────────────────
    "pack-cxl":                                 "PACK-CXL",
    "pack cxl":                                 "PACK-CXL",
    "photoactivated chromophore":               "PACK-CXL",
    "photoactivated chromophore for keratitis": "PACK-CXL",

    # ── Keratoconus variants ─────────────────────────────────────────────────
    "keratoconus":                              "keratoconus",
    "progressive keratoconus":                  "keratoconus",
    "pediatric keratoconus":                    "paediatric keratoconus",
    "paediatric keratoconus":                   "paediatric keratoconus",
    "childhood keratoconus":                    "paediatric keratoconus",

    # ── Cornea / ectasia variants ────────────────────────────────────────────
    "corneal ectasia":                          "corneal ectasia",
    "ectasia":                                  "corneal ectasia",
    "post-lasik ectasia":                       "post-refractive ectasia",
    "post lasik ectasia":                       "post-refractive ectasia",
    "iatrogenic ectasia":                       "post-refractive ectasia",
    "pellucid marginal degeneration":           "pellucid marginal degeneration",
    "pmd":                                      "pellucid marginal degeneration",

    # ── Riboflavin/UVA — keep as clinical concept, not just procedural label ─
    "riboflavin":                               "riboflavin",
    "vitamin b2":                               "riboflavin",
    "uva":                                      "ultraviolet-A (UVA)",
    "ultraviolet-a":                            "ultraviolet-A (UVA)",
    "ultraviolet a":                            "ultraviolet-A (UVA)",
    "uv-a":                                     "ultraviolet-A (UVA)",

    # ── Corneal topography/imaging ────────────────────────────────────────────
    "corneal topography":                       "corneal topography",
    "scheimpflug":                              "corneal topography",
    "pentacam":                                 "corneal topography",
    "corneal tomography":                       "corneal topography",
    "optical coherence tomography":             "OCT",
    "oct":                                      "OCT",
    "anterior segment oct":                     "OCT",

    # ── Biomechanics ─────────────────────────────────────────────────────────
    "corneal biomechanics":                     "corneal biomechanics",
    "corneal hysteresis":                       "corneal biomechanics",
    "ocular response analyzer":                 "corneal biomechanics",
    "corvis st":                                "corneal biomechanics",
    "young's modulus":                          "corneal biomechanics",
    "stress-strain":                            "corneal biomechanics",

    # ── Infectious keratitis ─────────────────────────────────────────────────
    "infectious keratitis":                     "infectious keratitis",
    "fungal keratitis":                         "infectious keratitis",
    "bacterial keratitis":                      "infectious keratitis",
    "acanthamoeba keratitis":                   "infectious keratitis",
    "microbial keratitis":                      "infectious keratitis",
    "corneal ulcer":                            "infectious keratitis",
}

# Terms to exclude entirely from keyword charts — too generic or purely procedural
_KW_EXCLUDE: set[str] = {
    "cornea",           # everything in the dataset involves the cornea
    "humans",           # MeSH noise
    "adult",
    "female",
    "male",
    "aged",
    "middle aged",
    "prospective studies",
    "retrospective studies",
    "treatment outcome",
    "follow-up studies",
    "visual acuity",    # near-universal in ophthalmology, not discriminating
    "refraction, ocular",
}


def _clean_keyword(kw: str) -> str | None:
    """
    Normalise a keyword: lowercase, strip punctuation, apply synonym map.
    Returns None if the term should be excluded entirely.
    """
    cleaned = kw.lower().strip().rstrip(".,;:")
    # Apply synonym map (exact match first, then substring for common prefixes)
    if cleaned in _KW_SYNONYMS:
        cleaned = _KW_SYNONYMS[cleaned]
    # Exclude generic terms
    if cleaned in _KW_EXCLUDE:
        return None
    return cleaned if cleaned else None


def keyword_stats(records: list[dict], use_mesh: bool = False) -> dict:
    """
    Returns:
      - freq: {keyword: count}
      - cooccurrence: {(kw1, kw2): count}  (edges for network)
    Synonymous keyword variants are merged before counting.
    """
    freq:  dict[str, int]   = collections.Counter()
    cooc:  dict[tuple, int] = collections.Counter()

    for rec in records:
        kws = rec.get("mesh", []) if use_mesh else rec.get("keywords", [])
        if use_mesh:
            kws = list(kws) + rec.get("keywords", [])

        # Clean, deduplicate, and exclude after synonym mapping
        cleaned = list({
            ck for k in kws
            if k.strip()
            for ck in [_clean_keyword(k)]
            if ck is not None
        })

        for k in cleaned:
            freq[k] += 1
        for k1, k2 in itertools.combinations(sorted(cleaned), 2):
            cooc[(k1, k2)] += 1

    # Filter by minimum frequency / co-occurrence
    freq_filtered = {k: v for k, v in freq.items() if v >= config.MIN_KEYWORD_FREQ}
    cooc_filtered = {k: v for k, v in cooc.items()
                     if v >= config.MIN_COOCCURRENCE
                     and k[0] in freq_filtered
                     and k[1] in freq_filtered}

    return {
        "freq":        freq_filtered,
        "cooccurrence": {f"{k[0]}|||{k[1]}": v for k, v in cooc_filtered.items()},
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. Institution analysis
# ─────────────────────────────────────────────────────────────────────────────

# ── Institution alias table ──────────────────────────────────────────────────
# Maps lowercase fragments → canonical institution name.
# Checked BEFORE the generic extractor. Add new entries here freely.
# Institution alias table now lives in data/institution_aliases.csv (institutions.py).

# ── Prefixes that indicate a sub-unit, NOT the institution itself ─────────────
# Any comma-separated segment STARTING with one of these should be SKIPPED.
_DEPT_PREFIXES = (
    # English department/division patterns
    "department of", "dept of", "dept.", "the department of",
    "a department of", "from the department",
    "division of", "div of",
    "section of", "unit of",
    "laboratory of", "lab of",
    "faculty of",
    "school of",                         # "School of Materials…", "School of Medicine"
    "institute of ophthalmology",        # too generic — thousands of institutions have this
    "research institute of eye",         # "Research Institute of Eye Diseases" alone = no institution
    "institute of biochemical",
    "ophthalmology department",
    "eye department",
    "optometry department",
    # German
    "augenklinik",                       # generic "eye clinic"
    "klinik für",                        # "Klinik für Augenheilkunde"
    "abteilung für",                     # "Abteilung für…" = department of
    "augenabteilung",
    # French
    "service d'ophtalmologie",
    "clinique ophtalmologique",
    "département d'ophtalmologie",
    # Spanish / Portuguese
    "centro de",
    "departamento de",
    "servicio de",
    # Italian
    "dipartimento di",
    "clinica oculistica",
    # Trailing stopwords that indicate incomplete affiliation
    "school of medicine",                # bare "School of Medicine" with no university
    "school of optometry",
    "college of medicine",
    # Specific strings reported from real data
    "division of clinical",              # "Division of Clinical Neuroscience" alone
    "research institute of eye diseases",# without a following university
    "institute of biochemical",
    "institute of biomedical",
)

# ── Tokens that strongly indicate a real institution ─────────────────────────
_INST_TOKENS = (
    "university", "université", "universität", "università", "universidad",
    "universidade", "universiteit", "universitetet",
    "hospital", "hôpital", "krankenhaus", "klinikum", "spital",
    "institute", "institut", "istituto",
    "college", "school of medicine", "medical school", "medical center",
    "medical centre", "eye centre", "eye center", "eye care",
    "eye hospital", "eye institute", "eye clinic",
    "nethralaya", "sankara", "aravind",   # named Indian eye centres
    "foundation", "academy",
    "clinic",
)


def _is_dept(segment: str) -> bool:
    """Return True if this segment looks like a department/sub-unit, not an institution."""
    sl = segment.lower().strip()
    return any(sl.startswith(p) for p in _DEPT_PREFIXES)


def _is_inst(segment: str) -> bool:
    """Return True if this segment looks like a genuine institution."""
    sl = segment.lower()
    return any(tok in sl for tok in _INST_TOKENS)


# ── Affiliation segmentation (added: fixes institution attribution) ───────────
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\.?")
_ATTRIB_RE = re.compile(r"\([A-Z][a-zA-Z'\-]+(?:,\s*[A-Z][a-zA-Z'\-]+)*\)")


def _affil_segments(affil: str, first_surname: str = "") -> list[str]:
    """Split one PubMed <Affiliation> element into individual institution segments.

    PubMed supplies an author's affiliations in two shapes that the naive
    parser mishandles:

    1. All affiliations joined into ONE element with semicolons.  Taking the
       whole string yields only the first institution and silently discards
       every other one the author listed.
    2. Journal-style combined blocks that list SEVERAL authors' affiliations
       with parenthesised name attributions, e.g.
       "Dept, Inst A, City (Smith, Jones); Dept, Inst B, City (Brown)".
       Parsing the whole string credits Inst A to every first author on such a
       paper, regardless of where that author actually works.

    A trailing corresponding-author e-mail also defeats the parser, which then
    returns fragments like "Switzerland. name@example.com".
    """
    s = _EMAIL_RE.sub("", affil or "").strip().rstrip(".").strip()
    if not s:
        return []
    if _ATTRIB_RE.search(s):
        parts = re.split(r";\s*", s)
        if first_surname:
            mine = [p for p in parts
                    if "(" in p and re.search(r"\b" + re.escape(first_surname) + r"\b", p)]
            if mine:
                return [p.strip() for p in mine if p.strip()]
        return [parts[0].strip()] if parts else []
    return [p.strip() for p in re.split(r";\s*", s) if p.strip()]


def _norm_institution(affil: str) -> str | None:
    """Canonical institution for one affiliation segment (see institutions.py)."""
    import institutions
    return institutions.resolve(affil).canonical


def institution_stats(records: list[dict],
                      first_author_only: bool = False,
                      level: str = "canonical",
                      counting: str = "primary",
                      top_n: int = 50) -> list[dict]:
    """Institutional publication and citation counts.

    first_author_only: True → the first author only (the originating group);
        False → all co-authors' institutions (inflates frequent co-authors).
    level: "canonical" | "parent" | "cluster" (institutions.py alias table).
    counting: "primary" → one institution per author (their first resolvable
        affiliation); "whole" → every institution the author lists, 1 each;
        "fractional" → every institution, 1/k each.
    Rows carry competition ranks (ties shown as '=n').  Use
    institution_stats_meta() to also get the unresolved counts.
    """
    rows, _ = institution_stats_meta(records, first_author_only, level, counting, top_n)
    return rows


def institution_stats_meta(records: list[dict], first_author_only: bool = False,
                           level: str = "canonical", counting: str = "primary",
                           top_n: int = 50) -> tuple[list[dict], dict]:
    import institutions
    counter: dict[str, float] = collections.Counter()
    cite_sum: dict[str, float] = collections.defaultdict(float)
    n_cited: dict[str, int] = collections.Counter()
    meta = {"n_records": len(records), "n_no_affiliation": 0, "n_unresolved": 0,
            "n_resolved": 0, "level": level, "counting": counting,
            "first_author_only": first_author_only}
    for rec in records:
        cc = rec.get("citation_count")
        authors = rec.get("authors", []) or []
        if first_author_only:
            authors = authors[:1]
        surname = (authors[0].get("last") or "") if authors else ""
        seen: dict[str, float] = {}
        any_affil = False
        for a in authors:
            if a.get("affils"):
                any_affil = True
            res = institutions.author_institutions(a, surname)
            if not res:
                continue
            if counting == "primary":
                res = res[:1]
            w = 1.0 / len(res) if counting == "fractional" else 1.0
            for r in res:
                name = r.at(level)
                if not name or len(name) < 4:
                    continue
                seen[name] = max(seen.get(name, 0.0), w)
        if first_author_only:
            if not any_affil:
                meta["n_no_affiliation"] += 1
            elif not seen:
                meta["n_unresolved"] += 1
            else:
                meta["n_resolved"] += 1
        for name, w in seen.items():
            counter[name] += w
            if cc is not None:
                cite_sum[name] += w * cc
                n_cited[name] += 1
    top = counter.most_common(top_n)
    counts = [round(v, 3) for _, v in top]
    ranks = institutions.competition_ranks([int(round(c)) if counting != "fractional" else c for c in counts])
    rows = []
    for (k, v), rk in zip(top, ranks):
        rows.append({"institution": k, "count": (int(round(v)) if counting != "fractional" else round(v, 2)),
                     "citations": int(round(cite_sum[k])), "n_cited_known": n_cited[k],
                     "rank": rk,
                     "pct_of_total": round(100 * v / len(records), 2) if records else 0.0,
                     "pct_of_resolved": (round(100 * v / meta["n_resolved"], 2)
                                         if first_author_only and meta["n_resolved"] else None)})
    return rows, meta


# ─────────────────────────────────────────────────────────────────────────────
# 7. Publication type breakdown
# ─────────────────────────────────────────────────────────────────────────────

def pubtype_stats(records: list[dict]) -> dict[str, int]:
    counter: dict[str, int] = collections.Counter()
    for rec in records:
        for pt in rec.get("pub_types", []):
            counter[pt] += 1
    return dict(counter.most_common())


# ─────────────────────────────────────────────────────────────────────────────
# 8. Language breakdown
# ─────────────────────────────────────────────────────────────────────────────

def language_stats(records: list[dict]) -> dict[str, int]:
    counter: dict[str, int] = collections.Counter()
    for rec in records:
        lang = rec.get("language", "Unknown") or "Unknown"
        counter[lang] += 1
    return dict(counter.most_common())


# ─────────────────────────────────────────────────────────────────────────────
# 9. Author collaboration network
# ─────────────────────────────────────────────────────────────────────────────

def author_collab_network(records: list[dict], top_n: int = None) -> dict:
    """
    Returns co-authorship network for top N authors by publication count.

    Strategy: compute ALL pairwise co-authorship edges across the full
    literature first, then select the top_n nodes by publication count.
    This means edges to highly-cited collaborators outside the top-N by
    volume are still captured — a top-30 author who co-authored with a
    lower-volume but notable collaborator will have that edge present.
    """
    top_n = top_n or config.TOP_N_AUTHORS

    # Pass 1: count publications and edges for ALL authors
    all_counts:  dict[str, int] = collections.Counter()
    all_edges:   dict[tuple, int] = collections.Counter()

    for rec in records:
        paper_authors = [
            a["author_id"] for a in rec.get("authors", [])
            if a.get("author_id") and a["author_id"] != "__collective__"
        ]
        unique = sorted(set(paper_authors))
        for aid in unique:
            all_counts[aid] += 1
        for a1, a2 in itertools.combinations(unique, 2):
            all_edges[(a1, a2)] += 1

    # Pass 2: select top_n nodes by publication count
    top_ids = {aid for aid, _ in all_counts.most_common(top_n)}

    # Pass 3: include edges where AT LEAST ONE endpoint is in top_n
    # (so a top-30 author's connection to a notable collaborator is visible)
    # but cap to edges where BOTH endpoints have ≥ MIN_PUBS to avoid noise
    MIN_PUBS = max(1, all_counts.most_common(top_n)[-1][1] // 3
                   if len(all_counts) >= top_n else 1)

    node_counts: dict[str, int] = {}
    edge_weights: dict[tuple, int] = {}

    for (a1, a2), w in all_edges.items():
        a1_top = a1 in top_ids
        a2_top = a2 in top_ids
        if not (a1_top or a2_top):
            continue
        # Both must meet minimum pub threshold to appear as nodes
        if all_counts[a1] < MIN_PUBS or all_counts[a2] < MIN_PUBS:
            continue
        node_counts[a1] = all_counts[a1]
        node_counts[a2] = all_counts[a2]
        edge_weights[(a1, a2)] = w

    # Ensure all top_n nodes appear even if isolated
    for aid in top_ids:
        if aid not in node_counts:
            node_counts[aid] = all_counts[aid]

    return {
        "nodes": dict(node_counts),
        "edges": {f"{k[0]}|||{k[1]}": v for k, v in edge_weights.items()},
    }


# ─────────────────────────────────────────────────────────────────────────────
# Master runner
# ─────────────────────────────────────────────────────────────────────────────

def run_analysis(records: list[dict]) -> dict:
    print("[analyze] Computing temporal trends …")
    temporal = temporal_trends(records)

    print("[analyze] Computing author statistics …")
    authors = author_stats(records)

    print("[analyze] Computing journal statistics …")
    journals = journal_stats(records)

    print("[analyze] Computing country statistics …")
    countries = country_stats(records)

    print("[analyze] Computing country collaboration network …")
    country_net = country_collab_network(records)

    print("[analyze] Computing keyword statistics …")
    kw_stats = keyword_stats(records, use_mesh=False)
    mesh_stats = keyword_stats(records, use_mesh=True)

    print("[analyze] Computing institution statistics …")
    institutions, institutions_meta = institution_stats_meta(
        records, first_author_only=True,
        level=getattr(config, "INSTITUTION_LEVEL", "canonical"),
        counting=getattr(config, "INSTITUTION_COUNTING", "primary"))
    institutions_all_authors = institution_stats(records, first_author_only=False, counting="whole")

    print("[analyze] Computing publication type breakdown …")
    pubtypes = pubtype_stats(records)

    print("[analyze] Computing language breakdown …")
    languages = language_stats(records)

    print("[analyze] Computing author collaboration network …")
    auth_net = author_collab_network(records)

    return {
        "n_records":     len(records),
        "temporal":      temporal,
        "authors":       authors,
        "journals":      journals,
        "countries":     countries,
        "country_net":   country_net,
        "keywords":      kw_stats,
        "mesh":          mesh_stats,
        "institutions":         institutions,
        "institutions_meta":    institutions_meta,
        "institutions_all":     institutions_all_authors,
        "pub_types":     pubtypes,
        "languages":     languages,
        "author_net":    auth_net,
    }


if __name__ == "__main__":
    # Quick test with cached data
    for fname in ["records_cited.json", "records_disambig.json", "records.json"]:
        p = pathlib.Path(config.CACHE_DIR) / fname
        if p.exists():
            with open(p) as f:
                records = json.load(f)
            break

    from geo import enrich_countries
    records = enrich_countries(records)
    results = run_analysis(records)

    out = pathlib.Path(config.DATA_DIR) / "analysis.json"
    with open(out, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nSaved analysis to {out}")
    print(f"Total records: {results['n_records']}")
    print(f"Unique authors (≥{config.MIN_AUTHOR_PUBS} pubs): {len(results['authors'])}")
    print(f"Journals: {len(results['journals'])}")
    print(f"Countries: {len(results['countries'])}")
