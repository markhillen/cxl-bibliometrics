"""Relevance filter tests — the cases the old filter got wrong."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import relevance


def _rec(pmid="1", title="", abstract="", journal="", abbr="", mesh=None, issn=""):
    return {"pmid": pmid, "title": title, "abstract": abstract, "journal": journal,
            "journal_abbr": abbr, "mesh": mesh or [], "has_abstract": bool(abstract),
            "issn_linking": issn}


def test_ophthalmic_plastic_journal_is_kept():
    r = _rec(journal="Ophthalmic plastic and reconstructive surgery",
             title="Corneal cross-linking after eyelid surgery",
             abstract="Riboflavin/UVA corneal cross-linking in keratoconus patients.")
    d = relevance.classify(r)
    assert d.keep and "ophthalmology_journal" in d.flags


def test_behavioral_journal_not_excluded_by_oral():
    r = _rec(journal="Behavioral neuroscience", title="Cornea and cross-linking",
             abstract="Corneal riboflavin ultraviolet-A cross-linking in a keratoconus model.")
    d = relevance.classify(r)
    assert d.keep


def test_biomaterials_scaffold_paper_excluded():
    r = _rec(journal="Biomaterials", title="Genipin-crosslinked collagen scaffold",
             abstract="Corneal stromal scaffold cross-linked with genipin for tissue engineering.")
    d = relevance.classify(r)
    assert not d.keep and d.stage == "journal" and d.rule_id == "journal.biomaterials"


def test_mesh_exclusion_needs_no_ocular_mesh():
    r = _rec(journal="American journal of transplantation",
             title="UV light crosslinking regresses corneal blood vessels",
             abstract="Riboflavin/UVA corneal cross-linking reduced corneal neovascularisation before keratoplasty.",
             mesh=["Blood Vessels", "Cornea", "Corneal Neovascularization"])
    d = relevance.classify(r)
    assert d.keep, d
    r2 = _rec(journal="Journal of vascular research", title="Crosslinking of aortic collagen",
              abstract="Collagen cross-linking in aortic tissue; no corneal content.",
              mesh=["Blood Vessels", "Aorta"])
    d2 = relevance.classify(r2)
    assert not d2.keep and d2.stage in ("journal", "mesh")


def test_content_check_uses_full_abstract():
    r = _rec(journal="Journal of clinical medicine", title="Pellucid marginal degeneration: a review",
             abstract="Management includes corneal cross-linking in PMD; corneal findings are reviewed.")
    d = relevance.classify(r)
    assert d.keep, d


def test_no_abstract_in_ophth_journal_kept_with_flag():
    r = _rec(journal="Cornea", title="Corneal collagen cross-linking: a letter")
    d = relevance.classify(r)
    assert d.keep and "no_abstract" in d.flags


def test_screening_queue_for_ambiguous_non_ophth_journal():
    r = _rec(journal="Photochemistry and photobiology", title="A fluorescent label for collagen amines",
             abstract="Cross-linking of type I collagen in tendon and cornea for wound closure.")
    d = relevance.classify(r)
    assert d.keep and "screen" in d.flags and d.stage == "screen"


def test_manual_decision_wins(tmp_path, monkeypatch):
    p = tmp_path / "manual_screening.csv"
    p.write_text("pmid,decision,reason,screened_by,date\n999,exclude,test,MH,2026-09-10\n")
    monkeypatch.setattr(relevance, "MANUAL_PATH", p)
    relevance.reset_manual_cache()
    r = _rec(pmid="999", journal="Cornea", title="Corneal cross-linking in keratoconus",
             abstract="Riboflavin UVA.")
    d = relevance.classify(r)
    assert not d.keep and d.stage == "manual"
    relevance.reset_manual_cache()
