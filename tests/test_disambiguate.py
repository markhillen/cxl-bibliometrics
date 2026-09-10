"""Disambiguation tests: the Seiler father/son and Hafezi cases the safelist exists for."""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import disambiguate as D


def _rec(pmid, authors, year="2015"):
    out = []
    for last, fore, initials, affil in authors:
        out.append({"last": last, "fore": fore, "initials": initials,
                    "affils": [affil] if affil else [], "orcid": "", "collective": ""})
    return {"pmid": pmid, "year": year, "authors": out}


ZH = "Institute for Refractive and Ophthalmic Surgery (IROC), Zurich, Switzerland."
BE = "Department of Ophthalmology, Inselspital, University of Bern, Bern, Switzerland."
ELZA = "ELZA Institute, Dietikon, Switzerland."
TEH = "Department of Plastic Surgery, Tehran University of Medical Sciences, Tehran, Iran."


def _ids(records):
    records, _ = D.assign_author_ids(records)
    return {(r["pmid"], a["last"], a["fore"] or a["initials"]): a["author_id"]
            for r in records for a in r["authors"]}


def test_seiler_senior_and_junior_stay_separate():
    recs = [
        _rec("1", [("Seiler", "Theo", "T", ZH), ("Hafezi", "Farhad", "F", ELZA), ("Koller", "Tobias", "T", ZH)]),
        _rec("2", [("Seiler", "", "T", ZH), ("Hafezi", "Farhad", "F", ELZA), ("Koller", "Tobias", "T", ZH)]),
        _rec("3", [("Seiler", "Theo G", "TG", BE), ("Hafezi", "Farhad", "F", ELZA), ("Koller", "Tobias", "T", ZH)]),
        _rec("4", [("Seiler", "", "TG", BE), ("Hafezi", "Farhad", "F", ELZA), ("Koller", "Tobias", "T", ZH)]),
        _rec("5", [("Seiler", "Theo Günter", "TG", BE), ("Hafezi", "Farhad", "F", ELZA), ("Frueh", "Beatrice", "B", BE)]),
    ]
    ids = _ids(recs)
    senior = {ids[("1", "Seiler", "Theo")], ids[("2", "Seiler", "T")]}
    junior = {ids[("3", "Seiler", "Theo G")], ids[("4", "Seiler", "TG")], ids[("5", "Seiler", "Theo Günter")]}
    assert len(senior) == 1, senior
    assert len(junior) == 1, junior
    assert senior.isdisjoint(junior), (senior, junior)


def test_hafezi_f_and_n_and_tehran_are_three_people():
    recs = [
        _rec("1", [("Hafezi", "Farhad", "F", ELZA), ("Kling", "Sabine", "S", ELZA)]),
        _rec("2", [("Hafezi", "", "F", ELZA), ("Kling", "Sabine", "S", ELZA), ("Torres-Netto", "Emilio", "EA", ELZA)]),
        _rec("3", [("Hafezi", "Nikki", "N", ELZA), ("Kling", "Sabine", "S", ELZA), ("Torres-Netto", "Emilio", "EA", ELZA)]),
        _rec("4", [("Hafezi", "Farhad", "F", TEH), ("Naghibzadeh", "Bijan", "B", TEH)]),
    ]
    ids = _ids(recs)
    f_elza = {ids[("1", "Hafezi", "Farhad")], ids[("2", "Hafezi", "F")]}
    assert len(f_elza) == 1
    assert ids[("3", "Hafezi", "Nikki")] not in f_elza
    assert ids[("4", "Hafezi", "Farhad")] not in f_elza


def test_common_surname_split_by_institution():
    WZ = "Eye Hospital, Wenzhou Medical University, Wenzhou, China."
    PK = "Peking University Third Hospital, Beijing, China."
    recs = [
        _rec("1", [("Zhang", "Li", "L", WZ), ("Chen", "Wei", "W", WZ)]),
        _rec("2", [("Zhang", "Li", "L", PK), ("Wang", "Yan", "Y", PK)]),
    ]
    ids = _ids(recs)
    assert ids[("1", "Zhang", "Li")] != ids[("2", "Zhang", "Li")]


def test_forename_abbreviation_merges():
    assert D._forenames_compatible("theo g", "theo günter")
    assert D._forenames_compatible("j bradley", "j b")            # second token abbreviated
    assert not D._forenames_compatible("j bradley", "james")     # different token counts
    assert not D._forenames_compatible("theo", "theo günter")
