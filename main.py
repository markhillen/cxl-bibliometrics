#!/usr/bin/env python3
"""
main.py — CXL Bibliometric Analysis Pipeline
=============================================
Orchestrates the full analysis pipeline:

  1. Fetch PubMed records (cached)
  2. Author disambiguation
  3. Country enrichment
  4. Citation enrichment (CrossRef)
  5. Bibliometric analysis
  6. Visualization
  7. Report generation (CSV + Excel)

Usage:
  python3 main.py --api-key YOUR_NCBI_KEY
  python3 main.py --api-key YOUR_NCBI_KEY --refresh      # force re-download
  python3 main.py --skip-fetch                           # use cached data only
  python3 main.py --skip-citations                       # skip CrossRef lookup
  python3 main.py --start-year 2001 --end-year 2025     # override date range
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
    parser.add_argument("--api-key",        default="",    help="NCBI API key")
    parser.add_argument("--refresh",        action="store_true", help="Force re-download from PubMed")
    parser.add_argument("--skip-fetch",     action="store_true", help="Use cached records only")
    parser.add_argument("--skip-citations", action="store_true", help="Skip CrossRef citation lookup")
    parser.add_argument("--skip-viz",       action="store_true", help="Skip chart generation")
    parser.add_argument("--start-year",     type=int, default=None)
    parser.add_argument("--end-year",       type=int, default=None)
    args = parser.parse_args()

    # ── Apply overrides ───────────────────────────────────────────────────
    import config
    if args.start_year:
        config.START_YEAR = args.start_year
    if args.end_year:
        config.END_YEAR = args.end_year
    if args.api_key:
        config.NCBI_API_KEY = args.api_key
    if args.skip_citations:
        config.FETCH_CITATIONS = False

    t0 = time.time()
    print("=" * 60)
    print("  CXL Bibliometric Analysis Pipeline")
    print(f"  Date range: {config.START_YEAR}–{config.END_YEAR}")
    print("=" * 60)

    # ── Step 1: Fetch ─────────────────────────────────────────────────────
    if not args.skip_fetch:
        if args.pmid_file:
            from fetch import run_fetch_from_pmids
            records = run_fetch_from_pmids(
                pmid_file=args.pmid_file,
                api_key=config.NCBI_API_KEY,
                force_refresh=args.refresh
            )
        else:
            from fetch import run_fetch
            records = run_fetch(api_key=config.NCBI_API_KEY, force_refresh=args.refresh)
    else:
        # Load from cache
        for fname in ["records_cited.json", "records_disambig.json", "records.json"]:
            p = pathlib.Path(config.CACHE_DIR) / fname
            if p.exists():
                print(f"[main] Loading {fname} …")
                with open(p) as f:
                    records = json.load(f)
                print(f"[main] Loaded {len(records)} records")
                break
        else:
            print("[main] ERROR: No cached records found. Run without --skip-fetch first.")
            sys.exit(1)

    # ── Step 2: Author disambiguation ─────────────────────────────────────
    disambig_path = pathlib.Path(config.CACHE_DIR) / "records_disambig.json"
    if not args.skip_fetch or not disambig_path.exists():
        from disambiguate import assign_author_ids
        records, _ = assign_author_ids(records)
        with open(disambig_path, "w") as f:
            json.dump(records, f, cls=_SetEncoder)
        print(f"[main] Saved disambiguated records")
    else:
        print(f"[main] Using pre-disambiguated records")
        if not any("author_id" in a for rec in records for a in rec.get("authors", [])):
            from disambiguate import assign_author_ids
            records, _ = assign_author_ids(records)

    # ── Step 3: Country enrichment ────────────────────────────────────────
    from geo import enrich_countries
    records = enrich_countries(records)
    print(f"[main] Country enrichment complete")

    # ── Step 4: Citation enrichment ───────────────────────────────────────
    cited_path = pathlib.Path(config.CACHE_DIR) / "records_cited.json"
    if config.FETCH_CITATIONS:
        from citations import enrich_citations
        records = enrich_citations(records)
        with open(cited_path, "w") as f:
            json.dump(records, f, cls=_SetEncoder)
        print(f"[main] Citation enrichment complete")
    else:
        print(f"[main] Citation enrichment skipped")

    # ── Step 5: Analysis ──────────────────────────────────────────────────
    from analyze import run_analysis
    results = run_analysis(records)

    analysis_path = pathlib.Path(config.DATA_DIR) / "analysis.json"
    with open(analysis_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"[main] Analysis saved to {analysis_path}")

    # ── Step 6: Visualizations ────────────────────────────────────────────
    if not args.skip_viz:
        from visualize import run_visualizations
        run_visualizations(results, records)

    # ── Step 7: Reports ───────────────────────────────────────────────────
    from report import generate_reports
    print("[main] Generating reports …")
    generate_reports(results)

    # ── Summary ───────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print()
    print("=" * 60)
    print("  PIPELINE COMPLETE")
    print(f"  Total records:   {results['n_records']}")
    print(f"  Unique authors:  {len(results['authors'])} (≥{config.MIN_AUTHOR_PUBS} pubs)")
    print(f"  Journals:        {len(results['journals'])}")
    print(f"  Countries:       {len(results['countries'])}")
    print(f"  Elapsed:         {elapsed:.1f}s")
    print(f"  Outputs in:      {config.OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
