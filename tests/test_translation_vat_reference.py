"""'בתוספת מע"מ' (plus VAT) is money, not a reference to an addendum. A live run flagged it as a missing
cross-reference, and the translator then told the client its automated check had failed."""
import importlib.util
import pathlib

P = pathlib.Path(__file__).resolve().parents[1] / "areolegal/skills/legal-contract-translator/scripts/translation_integrity_check.py"
spec = importlib.util.spec_from_file_location("tic", P)
tic = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tic)


def test_plus_vat_is_not_a_reference():
    assert tic.refs_of('החברה תשלם לספק תמורה חודשית בתוספת מע"מ, תוך 30 ימים') == []
    assert tic.refs_of("בתוספת מע״מ כדין") == []


def test_real_addendum_and_clause_references_still_count():
    assert tic.refs_of("לפי תוספת א להסכם") == ["a"]
    assert tic.refs_of("בהתאם לסעיף 3.1 ולנספח ב") == ["3.1", "b"]
