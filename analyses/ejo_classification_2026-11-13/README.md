# Trial, synthesis and registry classifications (EJO version, November 2026)

The classification record behind the trial analysis of the EJO manuscript
(randomized trials of corneal cross-linking: what they compare). Codes follow
the coding manual, `CXL RCT classification coding manual v1.1.docx`, applied
to titles and abstracts only.

How the codes were produced:

1. An AI assistant (Claude, Anthropic) drafted a classification with a stated
   reason for every candidate record, in two independent sessions.
2. Rater 1 (one author) confirmed or overruled every draft of the first
   session (350 records).
3. Rater 2 (a second author) reviewed every draft of the second session for
   the 160 records identified as trials, against the abstracts, and changed
   none. The files in `rater2/` are the sheets as returned on 9 November 2026;
   their names and the comments file record that the codes were AI-drafted.
4. A third author adjudicated the 16 disagreements between the two code sets
   (`adjudication/`). Agreement (Cohen's κ) is between the two author-reviewed,
   AI-drafted code sets.

The registry records (ClinicalTrials.gov, searched 13 November 2026) and the
abstract-screen synthesis candidates were coded in two independent AI sessions
without confirmation by an author.

Contents:

- `ai_drafts/`: the candidate sets (132 PubMed-tagged trial records, 218
  untagged screen candidates, 84 synthesis candidates) and the AI drafts.
- `rater1/rater1_MH_final_2026-11-03.csv`: Rater 1's final codes.
- `rater2/`: Rater 2's returned coding sheet and comments (9 November 2026).
- `adjudication/`: the adjudicator's returned sheet (16 decisions with
  reasons), the final codes after adjudication (`rct_final_codes_2026-11-13.csv`)
  and the agreement table.
- `registry_and_revision/`: the registry codes, the recall check, the per-year
  counts, the comparator ratios and the script that produced them
  (`revision_analyses.py`, 13 November 2026), with its summary.

The synthesis classifications confirmed by Rater 1 and the copy of Rater 1's
codes that Figure 2 reads are in `../ejo_recut/classification/`.
