import pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import keywords as K

def test_accelerated_family():
    for t in ["Accelerated corneal cross‑linking", "accelerated crosslinking", "A-CXL", "accelerated", "ACXL",
              "accelerated corneal collagen cross-linking", "Accelerated CXL"]:
        assert K.normalize(t) == "accelerated CXL", t

def test_transepithelial_family():
    for t in ["transepithelial", "Trans-epithelial cross-linking", "epi-on CXL", "epithelium-on", "iontophoresis"]:
        assert K.normalize(t) == "transepithelial (epi-on) CXL", t

def test_languages_and_case():
    assert K.normalize("kératocône") == "keratoconus"
    assert K.normalize("Keratoconus") == K.normalize("keratoconus") == "keratoconus"
    assert K.normalize("queratocono") == "keratoconus"

def test_cxl_variants_collapse():
    for t in ["Cross Linking", "cross-linking", "crosslinking", "CXL", "corneal collagen crosslinking", "Cross-linking (CXL)"]:
        assert K.normalize(t) == "corneal cross-linking (CXL)", t

def test_prk_and_uva():
    assert K.normalize("PRK") == K.normalize("photorefractive keratectomy")
    assert K.normalize("Ultraviolet-A (UVA)") == "ultraviolet-A (UVA)"

def test_coverage():
    recs = [{"year": "2010", "keywords": []}, {"year": "2010", "keywords": ["x"]}, {"year": "2011", "keywords": ["y"]}]
    cov = K.coverage_by_year(recs)
    assert cov[0] == {"year": 2010, "n_records": 2, "n_with_author_keywords": 1, "pct": 50.0}
    assert K.coverage_overall(recs)["pct"] == 66.7
