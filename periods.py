"""
periods.py — Multi-period bibliometric analysis
================================================
Slices the fetched CXL record set into multiple time windows and runs
the full bibliometric analysis pipeline on each, writing per-period
output subdirectories.

Time windows (defined in config.ANALYSIS_PERIODS):
  all_time  — 2001 to present (full CXL literature)
  last_20yr — 20 years to present
  last_15yr — 15 years to present
  last_10yr — 10 years to present
  last_5yr  —  5 years to present

Usage (called automatically by main.py):
    from periods import run_all_periods
    run_all_periods(records, output_root="output")
"""

import os
import pathlib

import config


def _filter_by_period(records: list[dict], start: int, end: int) -> list[dict]:
    """Return records whose publication year falls within [start, end] inclusive."""
    out = []
    for rec in records:
        try:
            yr = int(rec.get("year", 0))
        except (ValueError, TypeError):
            yr = 0
        if yr and start <= yr <= end:
            out.append(rec)
    return out


def run_all_periods(records: list[dict], output_root: str = None,
                    skip_viz: bool = False) -> dict:
    """
    Run the full analysis pipeline for every period defined in
    config.ANALYSIS_PERIODS.

    Returns a dict keyed by period label containing the analysis results
    for each window. Also writes per-period output subdirectories and
    a combined summary CSV.
    """
    import analyze
    import report
    import visualize

    output_root = output_root or config.OUTPUT_DIR
    all_results: dict[str, dict] = {}

    for label, start, end in config.ANALYSIS_PERIODS:
        period_records = _filter_by_period(records, start, end)
        n = len(period_records)
        if n == 0:
            print(f"[periods] {label}: no records — skipping")
            continue

        print(f"\n{'='*60}")
        print(f"[periods] {label}: {n:,} records ({start}–{end})")
        print(f"{'='*60}")

        # Per-period output directory
        period_dir = pathlib.Path(output_root) / label
        period_dir.mkdir(parents=True, exist_ok=True)

        # Override OUTPUT_DIR so visualize/report write to the period subdir
        _orig = config.OUTPUT_DIR
        config.OUTPUT_DIR = str(period_dir)

        try:
            results = analyze.run_analysis(period_records)
            report.generate_reports(results)
            if not skip_viz:
                visualize.run_visualizations(results, period_records)
        finally:
            config.OUTPUT_DIR = _orig

        # Compute field-level h-index now while period_records is in scope
        cite_counts = sorted(
            (rec.get("citation_count") or 0 for rec in period_records),
            reverse=True,
        )
        h_field = sum(1 for i, c in enumerate(cite_counts, 1) if c >= i)

        results["_period"] = {
            "label": label, "start": start, "end": end, "n": n
        }
        results["_h_index_field"] = h_field
        all_results[label] = results

    # ── Combined summary table ────────────────────────────────────────────────
    _write_period_summary(all_results, output_root)

    return all_results


def _write_period_summary(all_results: dict, output_root: str) -> None:
    """Write a single CSV comparing headline metrics across all time windows."""
    import csv

    rows = []
    for label, res in all_results.items():
        p = res.get("_period", {})
        n_pubs = p.get("n", 0)
        total_cites = sum(res.get("temporal", {}).get("citations", []))
        unique_authors = len(res.get("authors", []))
        unique_journals = len(res.get("journals", []))
        unique_countries = len(
            [c for c in res.get("countries", []) if c.get("country") != "Unknown"]
        )
        mean_cites = round(total_cites / n_pubs, 1) if n_pubs else ""
        rows.append({
            "period":             label,
            "start_year":         p.get("start", ""),
            "end_year":           p.get("end", ""),
            "total_publications": n_pubs,
            "total_citations":    total_cites,
            "unique_authors":     unique_authors,
            "unique_journals":    unique_journals,
            "unique_countries":   unique_countries,
            "mean_cites_per_pub": mean_cites,
            "h_index_field":      res.get("_h_index_field", ""),
        })

    outpath = pathlib.Path(output_root) / "period_comparison.csv"
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(outpath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"\n[periods] Period comparison saved → {outpath}")
