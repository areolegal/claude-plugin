# -*- coding: utf-8 -*-
"""`extract_corpus.py` על ספריית הייחוס: מה שנוסף, ומה שאסור שיאבד.

הקריאה עברה לקוד של ענבל (`lib/risk/extract_corpus.py`), והמבנה נשאר של
הגרסה הקודמת, כי ההוראות לשני הסקילים נשענות עליו. לכן הבדיקות כאן שני
סוגים:

* **מה שנוסף:** PDF; טקסט מוסתר (גופן לבן); תיבת טקסט; נוסח "דחה הכול"
  כשיש שינוי במעקב; ההערות עם הנוסח שהן מעוגנות בו.
* **מה שאסור שיאבד:** תא בטבלה נשאר עם הטבלה, השורה והעמודה שלו ("5,000"
  בלי "מחיר" אינו אומר דבר); מספר הסעיף; הערת שוליים וכותרת עליונה;
  כפילויות; סימון טיוטה.

ושני מקרים שבהם "לא נקרא" עדיף על "נקרא": PDF בעברית בלי pymupdf יוצא
הפוך, ולכן אינו נכנס כציטוט; ו-DOC אינו נקרא, עם הסיבה.
"""
import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPT = (PLUGIN / "areolegal" / "skills" / "contract-playbook-builder"
          / "scripts" / "extract_corpus.py")
PDF = LIB / "tests" / "fixtures"

docx = pytest.importorskip("docx")
from docx.oxml import parse_xml  # noqa: E402

W = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def _p(inner):
    return parse_xml('<w:p %s>%s</w:p>' % (W, inner))


def rich_docx(path):
    """הסכם קטן ובו כל מה שהקורא הקודם פספס, ומה שהוא כן ידע."""
    d = docx.Document()
    d.sections[0].header.paragraphs[0].text = "בין חברת הדוגמה בע\"מ לבין הספק בע\"מ"
    body = d.element.body
    d.add_paragraph("1. התמורה תשולם בתוך 30 יום מקבלת החשבונית.")
    # שינוי במעקב: "30" נמחק ו-"45" נוסף
    body.append(_p(
        '<w:r><w:t xml:space="preserve">2. תקופת ההודעה היא </w:t></w:r>'
        '<w:del w:id="1" w:author="יועץ"><w:r><w:delText>30</w:delText></w:r></w:del>'
        '<w:ins w:id="2" w:author="יועץ"><w:r><w:t>45</w:t></w:r></w:ins>'
        '<w:r><w:t xml:space="preserve"> יום.</w:t></w:r>'))
    # טקסט מוסתר: גופן לבן
    body.append(_p(
        '<w:r><w:t xml:space="preserve">3. האחריות מוגבלת לסכום התמורה. </w:t></w:r>'
        '<w:r><w:rPr><w:color w:val="FFFFFF"/></w:rPr><w:t>הספק מוותר על כל תקרה.</w:t></w:r>'))
    # תיבת טקסט
    body.append(_p(
        '<w:r><w:pict><v:shape xmlns:v="urn:schemas-microsoft-com:vml"><v:textbox>'
        '<w:txbxContent><w:p><w:r><w:t>נספח א: מחירון מעודכן</w:t></w:r></w:p></w:txbxContent>'
        '</v:textbox></v:shape></w:pict></w:r>'))
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "שירות", "מחיר"
    t.cell(1, 0).text, t.cell(1, 1).text = "ייעוץ", "5,000"
    d.save(str(path))
    return path


@pytest.fixture
def corpus(tmp_path):
    c = tmp_path / "הסכמים"
    c.mkdir()
    rich_docx(c / "הסכם שירותים.docx")
    return c


def _run(corpus, tmp_path, extra=()):
    out = tmp_path / "corpus.json"
    r = subprocess.run([sys.executable, str(SCRIPT), str(corpus), "--out", str(out)] + list(extra),
                       capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(out.read_text(encoding="utf-8")), r.stdout


def _doc(data, name):
    return next(d for d in data["documents"] if d["path"].endswith(name))


def test_a_table_cell_keeps_its_table_row_and_column(corpus, tmp_path):
    data, _ = _run(corpus, tmp_path)
    cells = [b for b in _doc(data, "הסכם שירותים.docx")["paragraphs"] if b["kind"] == "cell"]
    price = next(b for b in cells if b["text"] == "5,000")
    assert (price["table"], price["row"], price["col"]) == (1, 1, 1)
    assert _doc(data, "הסכם שירותים.docx")["table_count"] == 1


def test_a_tracked_change_carries_both_readings(corpus, tmp_path):
    data, _ = _run(corpus, tmp_path)
    d = _doc(data, "הסכם שירותים.docx")
    p = next(b for b in d["paragraphs"] if b["text"].startswith("2."))
    assert "45" in p["text"] and "30" not in p["text"]
    assert "30" in p["text_reject_all"] and "45" not in p["text_reject_all"]
    assert d["has_tracked_changes"] and d["looks_like_draft"]
    assert d["tracked_counts"]["ins"] == 1 and d["tracked_counts"]["del"] == 1


def test_hidden_text_is_found_and_reported(corpus, tmp_path):
    """גופן לבן הוא תנאי שהצד שכנגד מקווה שלא ייקרא."""
    data, printed = _run(corpus, tmp_path)
    d = _doc(data, "הסכם שירותים.docx")
    p = next(b for b in d["paragraphs"] if b["text"].startswith("3."))
    assert p["hidden"] and p["hidden"][0]["how"] == "color"
    assert "מוותר על כל תקרה" in p["hidden"][0]["text"]
    assert d["hidden_total"] == 1
    assert data["hidden_text_documents"] == [d["path"]]
    assert "עם טקסט מוסתר   : 1" in printed


def test_a_textbox_is_read_once(corpus, tmp_path):
    data, _ = _run(corpus, tmp_path)
    boxes = [b for b in _doc(data, "הסכם שירותים.docx")["paragraphs"]
             if "מחירון מעודכן" in b["text"]]
    assert len(boxes) == 1 and boxes[0]["kind"] == "textbox"


def test_the_header_and_the_clause_numbers_are_kept(corpus, tmp_path):
    data, _ = _run(corpus, tmp_path)
    d = _doc(data, "הסכם שירותים.docx")
    assert any(b["kind"] == "header_footer" and "חברת הדוגמה" in b["text"] for b in d["paragraphs"])
    first = next(b for b in d["paragraphs"] if b["text"].startswith("1."))
    assert first["clause"] == "1"


def test_an_exact_duplicate_is_counted_once(corpus, tmp_path):
    shutil.copy(corpus / "הסכם שירותים.docx", corpus / "הסכם שירותים - עותק.docx")
    data, _ = _run(corpus, tmp_path)
    assert data["document_count"] == 1 and data["duplicate_count"] == 1


def test_a_pdf_is_read_when_pymupdf_is_installed(corpus, tmp_path):
    pytest.importorskip("pymupdf")
    pdf = next(PDF.rglob("reshumot_sample.pdf"))
    shutil.copy(pdf, corpus / "חוק.pdf")
    data, _ = _run(corpus, tmp_path)
    d = _doc(data, "חוק.pdf")
    assert d["format"] == "pdf" and d["pdf_engine"] == "pymupdf"
    # סדר לוגי: המילה הראשונה של השורה היא הראשונה במחרוזת
    assert any(b["text"].startswith("מזמין שהוא עסק") for b in d["paragraphs"])
    assert data["pdf_count"] == 1 and not data["unreadable"]


def test_a_doc_file_is_unreadable_with_a_reason(corpus, tmp_path):
    (corpus / "ישן.doc").write_bytes(b"\xd0\xcf\x11\xe0 old word")
    data, printed = _run(corpus, tmp_path)
    assert any("ישן.doc" in u and "docx" in u for u in data["unreadable"])
    assert "ישן.doc" in printed


def test_a_hebrew_pdf_is_not_read_backwards_without_pymupdf(corpus, tmp_path, monkeypatch):
    """עם pypdf בלבד עברית יוצאת הפוכה. "לא נקרא" עדיף על ציטוט הפוך."""
    pytest.importorskip("pypdf")
    pdf = next(PDF.rglob("reshumot_sample.pdf"))
    shutil.copy(pdf, corpus / "חוק.pdf")
    blocker = tmp_path / "block"
    blocker.mkdir()
    for mod in ("pymupdf", "fitz"):
        (blocker / (mod + ".py")).write_text("raise ImportError('blocked for the test')\n")
    out = tmp_path / "corpus.json"
    env = dict(__import__("os").environ, PYTHONPATH=str(blocker))
    r = subprocess.run([sys.executable, str(SCRIPT), str(corpus), "--out", str(out)],
                       capture_output=True, text=True, cwd=str(SCRIPT.parent), env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert not any(d["path"].endswith("חוק.pdf") for d in data["documents"])
    assert any("חוק.pdf" in u and "pymupdf" in u for u in data["unreadable"])
