import pytest
from clm import doc_kind
from helpers import make_docx


@pytest.mark.parametrize("name,kind", [
    ("הסכם שכירות מחסן קירור עפולה - חתום 1.12.2021.docx", "signed"),
    ("RedVector - Statement of Work No. 1 - Penetration Test.docx", "order"),
    ("Babcom Reseller Agreement(9072101.1) (redline) 10-12-2025.docx", "negotiation_version"),
    ("גילוי דעת AI - נוסח סופי - צבע אחיד.docx", "non_agreement"),
    ("הסכם שירותי ייעוץ מקצועי - מבט נותן השירותים (דוגמה).docx", "template"),
    ("הסכם מיקור חוץ - הערות ספק מלא.docx", "negotiation_version"),
    ("Cloud Hosting Amendment No 2.pdf", "amendment"),
    ("נספח ב - רמות שירות.docx", "schedule"),
    ("Altivo Cloud - Online Customer Agreement.pdf", "draft"),
])
def test_suggest_from_name(name, kind):
    assert doc_kind.suggest(name)[0] == kind


def test_docx_signals_and_suggestion(tmp_path):
    p = tmp_path / "x.docx"
    make_docx(str(p), tracked=True, comments=True)
    s = doc_kind.docx_signals(str(p))
    assert s["readable"] and s["tracked_changes"] and s["comments"]
    assert doc_kind.suggest("הסכם שירותים.docx", s)[0] == "negotiation_version"


def test_blanks_mean_template(tmp_path):
    # עדכון לפי פריט 11: שורה שתוויתה "שם" או "חתימה" אינה נספרת, ולכן השדות הריקים כאן אינם בשורות חתימה
    p = tmp_path / "t.docx"
    make_docx(str(p), body_xml="".join('<w:p><w:r><w:t>התמורה: ______ ש"ח</w:t></w:r></w:p>' for _ in range(6)))
    assert doc_kind.suggest("הסכם.docx", doc_kind.docx_signals(str(p)))[0] == "template"


def test_signed_file_with_toc_and_signature_lines_stays_signed(tmp_path):
    p = tmp_path / "s.docx"
    lines = ["תוכן עניינים", "1. הגדרות ........ 2", "2. תקופה ........ 3", "3. תמורה ........ 4",
             "חתימה: ____________", "חתימה: ____________", "שם: ____________", "Signature: ________"]
    make_docx(str(p), body_xml="".join('<w:p><w:r><w:t>%s</w:t></w:r></w:p>' % t for t in lines))
    sig = doc_kind.docx_signals(str(p))
    assert sig["blanks"] == 0
    assert doc_kind.suggest("הסכם שירותים - חתום.docx", sig)[0] == "signed"
    # גם כשיש שדות ריקים רבים בגוף, שם קובץ "חתום" גובר על כלל השדות הריקים
    blanks = {"readable": True, "tracked_changes": False, "comments": False, "blanks": 9}
    assert doc_kind.suggest("הסכם שירותים - חתום.docx", blanks)[0] == "signed"


@pytest.mark.parametrize("name", ["agreement unsigned.docx", "הסכם - לא חתום.docx", "Services UNSIGNED.pdf",
                                  "הסכם לא-חתום.docx"])
def test_unsigned_names_are_not_signed(name):
    assert doc_kind.suggest(name)[0] != "signed"


def test_negotiation_reason_uses_glossary_term():
    assert doc_kind.suggest("הסכם - הערות.docx")[1] == ["שם הקובץ מעיד על טיוטה עם הערות"]


def test_unreadable_docx(tmp_path):
    p = tmp_path / "bad.docx"
    p.write_bytes(b"not a zip")
    assert doc_kind.docx_signals(str(p)) == {"readable": False}


def test_says_draft_by_file_name():
    for name in ("x/תיקון 1 - טיוטה.docx", "x/Amendment draft.docx", "x/amendment (redline).docx",
                 "x/תיקון - הערות ספק.docx", "x/amendment unsigned.docx", "x/תיקון לא חתום.docx"):
        assert doc_kind.says_draft(name), name
    for name in ("x/תיקון 1 - חתום.docx", "x/Amendment 1 signed.docx"):
        assert not doc_kind.says_draft(name), name
