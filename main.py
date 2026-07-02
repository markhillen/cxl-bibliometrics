#!/usr/bin/env python3
"""
main.py — CXL Bibliometric Analysis Pipeline
=============================================
Orchestrates the full analysis pipeline:

  1. Fetch PubMed records (cached)          — query: corneal cross-linking
  2. Relevance filtering                    — expel non-ophthalmic records
  3. Author disambiguation                  — 4-layer heuristic + safelists
  4. Country enrichment                     — affiliation → ISO country
  5. Citation enrichment (CrossRef)         — by DOI
  6. Multi-period bibliometric analysis     — all-time / last 20/15/10/5 years
  7. Visualization                          — figures per period (PDF)
  8. Report generation                      — CSV + Excel per period
  9. Period comparison summary              — headline metrics across all windows

Usage:
  python3 main.py --api-key YOUR_NCBI_KEY
  python3 main.py --api-key YOUR_NCBI_KEY --refresh          # force re-download
  python3 main.py --skip-fetch                               # use cached data
  python3 main.py --skip-citations                           # skip CrossRef
  python3 main.py --pmid-file pmids_expanded.txt             # use PMID list
  python3 main.py --period all_time                          # single period only
  python3 main.py --skip-fetch --skip-citations              # figures/reports only
"""

import argparse
import json
import pathlib
import sys
import time


class _SetEncoder(json.JSONEncoder):
    """Convert sets to sorted lists for JSON serialisation."""
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(obj)
        return super().default(obj)


sys.path.insert(0, str(pathlib.Path(__file__).parent))


def main():
    parser = argparse.ArgumentParser(
        description="CXL Bibliometric Analysis Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--api-key",        default="",   help="NCBI API key")
    parser.add_argument("--pmid-file",      default="",   help="Path to PMID list file")
    parser.add_argument("--refresh",        action="store_true", help="Force re-download")
    parser.add_argument("--skip-fetch",     action="store_true", help="Use cached records only")
    parser.add_argument("--skip-citations", action="store_true", help="Skip CrossRef lookup")
    parser.add_argument("--skip-viz",       action="store_true", help="Skip chart generation")
    parser.add_argument("--use-openalex",   action="store_true",
                        help="Hybrid mode: overlay OpenAlex citations + ROR country "
                             "(needs cache/openalex_cache.json from openalex_enrich.py)")
    parser.add_argument("--period",         default="",
                        help="Run a single period only (e.g. all_time, last_10yr)")
    parser.add_argument("--start-year",     type=int, default=None,
                        help="Override ALL_TIME_START in config")
    parser.add_argument("--end-year",       type=int, default=None,
                        help="Override END_YEAR in config")
    args = parser.parse_args()

    # ── Verify dependencies before doing any work ──────────────────────────────
    try:
        import check_deps
        if check_deps.check():
            sys.exit(1)
    except ImportError:
        pass  # check_deps.py not present — proceed and let imports fail naturally

    import config

    # ── Config overrides ──────────────────────────────────────────────────────
    if args.api_key:
        config.NCBI_API_KEY = args.api_key
    if args.skip_citations:
        config.FETCH_CITATIONS = False
    if args.start_year is not None:
        config.ALL_TIME_START = args.start_year
        config.START_YEAR     = args.start_year
    if args.end_year is not None:
        config.END_YEAR = args.end_year

    # Rebuild periods if date overrides were applied
    if args.start_year is not None or args.end_year is not None:
        s = config.ALL_TIME_START
        e = config.END_YEAR
        config.ANALYSIS_PERIODS = [
            ("all_time",  s,      e),
            ("last_20yr", e - 19, e),
            ("last_15yr", e - 14, e),
            ("last_10yr", e - 9,  e),
            ("last_5yr",  e - 4,  e),
        ]

    # Filter to a single period if requested
    if args.period:
        config.ANALYSIS_PERIODS = [
            p for p in config.ANALYSIS_PERIODS if p[0] == args.period
        ]
        if not config.ANALYSIS_PERIODS:
            print(f"[main] ERROR: Unknown period '{args.period}'.")
            sys.exit(1)

    pathlib.Path(config.CACHE_DIR).mkdir(parents=True, exist_ok=True)
    pathlib.Path(config.OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print("=" * 60)
    print(f"  {config.PROJECT_NAME} v{config.PROJECT_VERSION}")
    print(f"  All-time fetch: {config.ALL_TIME_START}–{config.END_YEAR}")
    print(f"  Periods: {[p[0] for p in config.ANALYSIS_PERIODS]}")
    print("=" * 60)

    # ── Step 1: Fetch ─────────────────────────────────────────────────────────
    print(f"\n[1/8] Fetching records …")
    cited_path  = pathlib.Path(config.CACHE_DIR) / "records_cited.json"
    disamb_path = pathlib.Path(config.CACHE_DIR) / "records_disambig.json"
    raw_path    = pathlib.Path(config.CACHE_DIR) / "records.json"

    if args.skip_fetch:
        for p in [cited_path, disamb_path, raw_path]:
            if p.exists():
                print(f"[main] Loading {p.name} from cache …")
                with open(p) as f:
                    records = json.load(f)
                print(f"[main] {len(records):,} records loaded")
                break
        else:
            print("[main] ERROR: No cached records. Run without --skip-fetch first.")
            sys.exit(1)
    else:
        if args.pmid_file:
            from fetch import run_fetch_from_pmids
            records = run_fetch_from_pmids(
                pmid_file=args.pmid_file,
                api_key=config.NCBI_API_KEY,
                force_refresh=args.refresh,
            )
        else:
            from fetch import run_fetch
            records = run_fetch(api_key=config.NCBI_API_KEY, force_refresh=args.refresh)
    print(f"[main] {len(records):,} records after fetch + filtering")

    # ── Step 2: Author disambiguation ─────────────────────────────────────────
    print(f"\n[2/8] Disambiguating authors …")
    has_ids = any(
        a.get("author_id")
        for rec in records[:50]
        for a in rec.get("authors", [])
    )
    if args.skip_fetch and has_ids:
        print("[main] Author IDs already present — skipping disambiguation")
    else:
        from disambiguate import assign_author_ids
        records, _ = assign_author_ids(records)
        with open(disamb_path, "w") as f:
            json.dump(records, f, cls=_SetEncoder)
        print("[main] Disambiguation complete")

    # ── Step 3: Country enrichment ────────────────────────────────────────────
    print(f"\n[3/8] Enriching countries …")
    from geo import enrich_countries
    records = enrich_countries(records)
    print("[main] Country enrichment complete")

    # ── Step 4: Citation enrichment ───────────────────────────────────────────
    print(f"\n[4/8] Citation enrichment …")
    if config.FETCH_CITATIONS:
        from citations import enrich_citations
        records = enrich_citations(records)
        with open(cited_path, "w") as f:
            json.dump(records, f, cls=_SetEncoder)
        print("[main] Citations enriched and cached")
    else:
        print("[main] Skipped (--skip-citations)")

    # ── Step 4.5: OpenAlex hybrid overlay ─────────────────────────────────────
    if args.use_openalex:
        print(f"\n[4.5] Applying OpenAlex hybrid overlay …")
        from openalex_integrate import overlay, load_cache, author_disagreements
        oa = load_cache()
        if not oa:
            print("[main] WARNING: --use-openalex set but cache/openalex_cache.json "
                  "not found. Run: python3 openalex_enrich.py")
        else:
            records, _ = overlay(records, oa)
            report = author_disagreements(records)
            rep_path = pathlib.Path(config.OUTPUT_DIR) / "openalex_author_disagreements.md"
            rep_path.write_text(report)
            print(f"[main] Author-disagreement report: {rep_path}")

    # ── Steps 5–8: Multi-period analysis, viz, reports ────────────────────────
    print(f"\n[5–8/8] Running multi-period analysis …")
    from periods import run_all_periods
    all_results = run_all_periods(
        records,
        output_root=config.OUTPUT_DIR,
        skip_viz=args.skip_viz,
    )

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print("  PIPELINE COMPLETE")
    for label, res in all_results.items():
        p = res.get("_period", {})
        print(f"  {label:<14}  {p.get('n', '?'):>6,} records  "
              f"({p.get('start', '?')}–{p.get('end', '?')})")
    print(f"\n  Elapsed:   {elapsed:.1f}s")
    print(f"  Output:    {config.OUTPUT_DIR}/")
    print("=" * 60)


if __name__ == "__main__":
    main()
