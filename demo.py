#!/usr/bin/env python3
"""
demo.py — Test the full pipeline with synthetic CXL data
=========================================================
Generates 500 realistic synthetic PubMed records and runs
the complete analysis + visualization pipeline.
Run:  python3 demo.py
"""

import json
import random
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import config

random.seed(42)

# ── Synthetic data parameters ────────────────────────────────────────────────

AUTHORS_POOL = [
    # (last, fore, institution, country)
    ("Hafezi", "Farhad",       "University of Zurich",              "Switzerland"),
    ("Kymionis", "George D",   "University of Crete",               "Greece"),
    ("Wollensak", "Gregor",    "University of Berlin",              "Germany"),
    ("Spoerl", "Eberhard",     "Dresden University",                "Germany"),
    ("Vinciguerra", "Paolo",   "Milan Eye Center",                  "Italy"),
    ("Randleman", "Bradley J", "Emory University",                  "United States"),
    ("Rabinowitz", "Yaron S",  "Cedars-Sinai Medical Center",       "United States"),
    ("Hashemi", "Hassan",      "Noor Eye Hospital",                 "Iran"),
    ("Caporossi", "Aldo",      "University of Siena",               "Italy"),
    ("Mazzotta", "Cosimo",     "University of Siena",               "Italy"),
    ("Kanellopoulos", "A John","Laservision Institute",             "Greece"),
    ("Shetty", "Rohit",        "Narayana Nethralaya",               "India"),
    ("Tan", "Donald",          "Singapore National Eye Centre",     "Singapore"),
    ("Chan", "Elsie",          "Singapore National Eye Centre",     "Singapore"),
    ("Waring", "George O",     "Emory University",                  "United States"),
    ("Nuijts", "Rudy MMA",     "Maastricht University",             "Netherlands"),
    ("Elsheikh", "Ahmed",      "University of Liverpool",           "United Kingdom"),
    ("Qiu", "Ming",            "Wenzhou Medical University",        "China"),
    ("Zhang", "Lei",           "Peking University",                 "China"),
    ("Wang", "Yi",             "Tianjin Eye Hospital",              "China"),
    ("Alio", "Jorge L",        "University of Alicante",            "Spain"),
    ("Sekundo", "Walter",      "University of Marburg",             "Germany"),
    ("Hersh", "Peter S",       "Rutgers University",                "United States"),
    ("Sack", "David",          "Johns Hopkins University",          "United States"),
    ("Goldich", "Yakov",       "Tel Aviv University",               "Israel"),
    ("Sharma", "Namrata",      "AIIMS",                             "India"),
    ("Vajpayee", "Rasik B",    "Royal Victorian Eye Hospital",      "Australia"),
    ("Saelens", "Inge",        "University of Ghent",               "Belgium"),
    ("Koller", "Tobias",       "University of Zurich",              "Switzerland"),
    ("Belin", "Michael W",     "University of Arizona",             "United States"),
]

JOURNALS_POOL = [
    ("Cornea",                                      "Cornea"),
    ("Journal of Refractive Surgery",               "J Refract Surg"),
    ("Investigative Ophthalmology & Visual Science","Invest Ophthalmol Vis Sci"),
    ("Journal of Cataract and Refractive Surgery",  "J Cataract Refract Surg"),
    ("American Journal of Ophthalmology",           "Am J Ophthalmol"),
    ("British Journal of Ophthalmology",            "Br J Ophthalmol"),
    ("Ophthalmology",                               "Ophthalmology"),
    ("Eye",                                         "Eye"),
    ("Acta Ophthalmologica",                        "Acta Ophthalmol"),
    ("Clinical Ophthalmology",                      "Clin Ophthalmol"),
    ("Graefe's Archive for Clinical Ophthalmology", "Graefes Arch Clin Exp Ophthalmol"),
    ("Contact Lens & Anterior Eye",                 "Cont Lens Anterior Eye"),
    ("Optics Express",                              "Opt Express"),
    ("PLoS ONE",                                    "PLoS One"),
]

KEYWORDS_POOL = [
    "corneal cross-linking", "keratoconus", "riboflavin", "ultraviolet-a",
    "corneal ectasia", "biomechanics", "demarcation line", "keratometry",
    "corneal topography", "LASIK", "photorefractive keratectomy", "PRK",
    "epithelium-off CXL", "transepithelial CXL", "accelerated CXL",
    "progressive keratoconus", "corneal collagen", "stroma", "optical coherence tomography",
    "corneal thickness", "infectious keratitis", "bacterial keratitis",
    "fungal keratitis", "Acanthamoeba", "PACK-CXL", "pediatric keratoconus",
    "safety", "efficacy", "long-term outcomes", "keratocyte",
    "anterior segment OCT", "Scheimpflug", "corneal hysteresis",
    "intraocular pressure", "corneal biomechanics", "corneal stiffness",
    "collagen fibres", "reactive oxygen species", "photooxidation",
    "corneal scarring", "refractive error", "myopia", "astigmatism",
    "intrastromal corneal ring segments", "ICRS", "pellucid marginal degeneration",
    "post-LASIK ectasia", "collagen cross-linking", "ocular surface",
]

MESH_POOL = [
    "Corneal Cross-Linking", "Keratoconus", "Cornea", "Collagen",
    "Riboflavin", "Ultraviolet Rays", "Corneal Diseases", "Keratectasia",
    "Biomechanical Phenomena", "Photosensitizing Agents", "Corneal Stroma",
    "Refractive Surgical Procedures", "Keratomileusis, Laser In Situ",
    "Photorefractive Keratectomy", "Corneal Topography", "Visual Acuity",
    "Corneal Thickness", "Keratitis", "Anti-Infective Agents",
    "Treatment Outcome", "Follow-Up Studies", "Prospective Studies",
    "Retrospective Studies", "Randomized Controlled Trials as Topic",
]

PUB_TYPES_POOL = [
    ("Journal Article", 0.60),
    ("Journal Article|Clinical Trial", 0.10),
    ("Journal Article|Randomized Controlled Trial", 0.06),
    ("Journal Article|Review", 0.10),
    ("Journal Article|Meta-Analysis", 0.03),
    ("Journal Article|Case Reports", 0.05),
    ("Journal Article|Comparative Study", 0.04),
    ("Journal Article|Letter", 0.02),
]


def _pick_weighted(pool):
    r = random.random()
    cum = 0
    for item, p in pool:
        cum += p
        if r < cum:
            return item
    return pool[-1][0]


def _make_record(pmid: int, year: int) -> dict:
    # Pick journal
    jname, jabbr = random.choice(JOURNALS_POOL)

    # Pick authors (2–8)
    n_auth = random.choices([1, 2, 3, 4, 5, 6, 7, 8],
                             weights=[1, 4, 8, 10, 8, 5, 3, 2])[0]
    auth_sample = random.sample(AUTHORS_POOL, min(n_auth, len(AUTHORS_POOL)))
    authors = []
    for last, fore, inst, country in auth_sample:
        authors.append({
            "last":      last,
            "fore":      fore,
            "initials":  "".join(w[0] for w in fore.split()),
            "affils":    [f"Department of Ophthalmology, {inst}, {country}"],
            "orcid":     "",
            "collective":"",
        })

    # Keywords (3–8)
    kw_count = random.randint(3, 8)
    kws = random.sample(KEYWORDS_POOL, kw_count)

    # MeSH (3–6)
    mesh_count = random.randint(3, 6)
    mesh = random.sample(MESH_POOL, mesh_count)

    # Pub type
    pt_str = _pick_weighted(PUB_TYPES_POOL)
    pub_types = pt_str.split("|")

    # Simulated citations: older papers get more, with noise
    age = 2025 - year
    base_cites = max(0, int(age * random.expovariate(1 / 8) * random.uniform(0.5, 2.5)))
    # Top author papers get boosted
    if any(a["last"] in ["Hafezi", "Wollensak", "Kymionis", "Caporossi"]
           for a in authors):
        base_cites = int(base_cites * random.uniform(1.5, 4.0))

    return {
        "pmid":         str(pmid),
        "year":         str(year),
        "month":        str(random.randint(1, 12)),
        "title":        f"CXL study: {random.choice(kws)} in {random.choice(['keratoconus', 'ectasia', 'keratitis'])} — synthetic record {pmid}",
        "abstract":     "This is a synthetic abstract for testing purposes. " * 5,
        "journal":      jname,
        "journal_abbr": jabbr,
        "issn":         f"0000-{pmid % 9999:04d}",
        "volume":       str(year - 1990),
        "issue":        str(random.randint(1, 12)),
        "doi":          f"10.1234/cxl.{pmid}",
        "pub_types":    pub_types,
        "authors":      authors,
        "mesh":         mesh,
        "keywords":     kws,
        "grants":       [],
        "language":     random.choices(["eng", "fre", "ger", "spa"], weights=[85, 5, 5, 5])[0],
        "pub_country":  auth_sample[0][3] if auth_sample else "Unknown",
        "citation_count": base_cites,
    }


def generate_synthetic_records(n: int = 500) -> list[dict]:
    """Generate n synthetic CXL PubMed records with realistic year distribution."""
    # Year distribution: slow growth 2001-2009, acceleration 2010-2025
    year_weights = {}
    for y in range(2001, 2026):
        if y < 2005:
            year_weights[y] = 1
        elif y < 2010:
            year_weights[y] = 3
        elif y < 2015:
            year_weights[y] = 8
        elif y < 2020:
            year_weights[y] = 14
        else:
            year_weights[y] = 18

    years_list  = list(year_weights.keys())
    year_probs  = [year_weights[y] for y in years_list]
    total_w     = sum(year_probs)
    year_probs  = [w / total_w for w in year_probs]

    records = []
    for i in range(n):
        year = random.choices(years_list, weights=year_probs)[0]
        records.append(_make_record(40_000_000 + i, year))
    return records


def run_demo():
    print("=" * 60)
    print("  CXL Bibliometric Pipeline — DEMO MODE")
    print("  (Using 500 synthetic records)")
    print("=" * 60)

    # Generate synthetic data
    print("\n[demo] Generating synthetic records …")
    records = generate_synthetic_records(500)
    print(f"[demo] Generated {len(records)} records")

    # Save to cache
    cache = pathlib.Path(config.CACHE_DIR)
    cache.mkdir(parents=True, exist_ok=True)
    cache_file = cache / "records.json"
    with open(cache_file, "w") as f:
        json.dump(records, f)

    # ── Run pipeline ──────────────────────────────────────────────────────
    from disambiguate import assign_author_ids
    records, _ = assign_author_ids(records)

    from geo import enrich_countries
    records = enrich_countries(records)

    # Citations already in synthetic data — skip CrossRef
    config.FETCH_CITATIONS = False

    from analyze import run_analysis
    results = run_analysis(records)

    data_dir = pathlib.Path(config.DATA_DIR)
    data_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = data_dir / "analysis.json"
    with open(analysis_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    from visualize import run_visualizations
    run_visualizations(results, records)

    from report import generate_reports
    print("[demo] Generating reports …")
    generate_reports(results)

    print()
    print("=" * 60)
    print("  DEMO COMPLETE")
    print(f"  Records:   {results['n_records']}")
    print(f"  Authors:   {len(results['authors'])}")
    print(f"  Journals:  {len(results['journals'])}")
    print(f"  Countries: {len(results['countries'])}")
    print(f"  Outputs:   {config.OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    run_demo()
