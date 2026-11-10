# EJO re-cut (European Journal of Ophthalmology version, November 2026)

Analyses added for the EJO version of the manuscript (V24). They read the
cached records of the 23 September 2026 run (`cache/records_disambig.json`,
`cache/records_cited.json`) restricted to the frozen corpus
`data/pmids_final_corpus_2026-09-10.txt` (3,223 records). No network access.
Moved here from the untracked `output/ejo_recut/` on 10 November 2026; rerunning
both scripts reproduced every CSV byte for byte.

- `recut_institutions.py`: institution tables by all-author primary
  affiliation, with missing affiliations imputed from the same author's record
  within 2 years. Writes the baseline tables and the tables under the extended
  ELZA rule decided on 2 November 2026: from 2015 onwards, where F. Hafezi's
  first-listed affiliation resolves to the University of Zurich (incl. CABMM),
  the paper is credited to the ELZA Institute. IROC and non-Zurich affiliations
  are left as stated; whole and fractional counting are unchanged by the rule.
  `elzarule_reassigned_records.csv` lists the 31 reassigned records.
- `fig2_trials_vs_syntheses.py`: Figure 2, new randomized trials vs systematic
  reviews and meta-analyses of CXL per year (2009–2025), with `fig2_data.csv`.

`classification/` holds copies, taken 10 November 2026, of the two
classification files Figure 2 reads, from the paper folder's
`03 Supplemental Content/RCT classification`:

- `rater1_MH_final_2026-11-03.csv`: Rater 1 trial classification.
- `CXL SR-MA check Fable drafts for MH confirmation.xlsx`: systematic-review
  and meta-analysis check.

These classifications are provisional: the second-rater coding and the
consensus round were still open on 10 November 2026. Rerun Figure 2 on the
final files with `python3 analyses/ejo_recut/fig2_trials_vs_syntheses.py <folder>`.
