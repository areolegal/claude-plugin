# -*- coding: utf-8 -*-
"""טיוטה של הצד שכנגד שמגיעה עם שינויים פתוחים (עקוב אחר שינויים שלהם).

דיווח מהשטח (20.10.2026), אומת ושוחזר: כל טיוטה כזו נכשלה בנושא ונותן, גם כשההכרעה היחידה הייתה בועה.
1. `verify_roundtrip` השווה את "דחה הכול" לטיוטה שהתקבלה. "דחה הכול" דוחה גם את ההוספות שלהם, והטיוטה
   שהתקבלה מכילה אותן, ולכן ההשוואה נכשלה תמיד.
2. `qa_gate`: אותה השוואה (RT_REJECT); ובנוסף PKG_AUTHOR פסל כל מחבר אחר, גם את הצד שכנגד עצמו.
3. `apply_redlines.py` קרס בהדפסת הכשל (`"%s" % tuple`), והסתיר את הסיבה.
4. מאז 18.10 השכבה הפנימית אינה מופקת כברירת מחדל, והשער דרש בכל זאת כותרת פנימית בקובץ העבודה.
באף טיוטת בדיקה לא היו שינויים פתוחים של הצד שכנגד, ולכן אף בדיקה לא תפסה את זה.
"""
import hashlib
import json
import subprocess
import sys
import zipfile
from collections import Counter
from pathlib import Path
import re

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
ORCH = PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator" / "scripts"
sys.path[:0] = [str(LIB), str(ORCH)]
pytest.importorskip("docx")

from common import docx_tracked as dt  # noqa: E402
from lxml import etree  # noqa: E402

THEM = "Contractor Legal"
US = 'עו"ד דנה לוי'


@pytest.fixture
def received(tmp_path):
    from docx import Document
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    d = Document()

    def p(xs):
        para = d.add_paragraph()
        para._p.append(parse_xml('<w:pPr %s><w:bidi/></w:pPr>' % nsdecls("w")))
        for x in xs:
            para._p.append(parse_xml(x))
    r = lambda t: '<w:r %s><w:rPr><w:rtl/></w:rPr><w:t xml:space="preserve">%s</w:t></w:r>' % (nsdecls("w"), t)
    rev = lambda kind, t, i: ('<w:%s %s w:id="%d" w:author="%s" w:date="2026-10-19T10:00:00Z"><w:r><w:rPr><w:rtl/>'
                              '</w:rPr><w:%s xml:space="preserve">%s</w:%s></w:r></w:%s>'
                              % (kind, nsdecls("w"), i, THEM, "t" if kind == "ins" else "delText", t,
                                 "t" if kind == "ins" else "delText", kind))
    p([r("1. הספק יעמיד את השירות "), rev("ins", "בזמינות של 99.9% ", 1), r("לפי ההסכם.")])
    p([r("2. התשלום יבוצע בתנאי שוטף + "), rev("del", "30", 2), rev("ins", "90", 3), r(" ימים.")])
    p([r("3. על ההסכם יחול הדין הישראלי.")])
    path = tmp_path / "received.docx"
    d.save(path)
    prof = tmp_path / "profile.json"
    prof.write_text(json.dumps({"organization_name": "EXAMPLECO", "lawyer_name": US, "lawyer_initials": "דל"},
                               ensure_ascii=False), encoding="utf-8")
    return {"draft": path, "profile": prof, "dir": tmp_path}


def _decisions(r, items):
    path = r["dir"] / "dec.json"
    path.write_text(json.dumps({"transaction_id": "t", "round": 2, "author": US, "initials": "דל",
                                "received_sha256": hashlib.sha256(r["draft"].read_bytes()).hexdigest(),
                                "decisions": items}, ensure_ascii=False), encoding="utf-8")
    return path


def _apply(r, dec):
    out = r["dir"] / "work.docx"
    p = subprocess.run([sys.executable, "-B", str(ORCH / "apply_redlines.py"), "--draft", str(r["draft"]),
                        "--decisions", str(dec), "--profile", str(r["profile"]), "--out", str(out)],
                       capture_output=True, text=True)
    return p, out


def test_a_comment_only_answer_to_a_redlined_draft_passes(received):
    dec = _decisions(received, [{"id": "D1", "op": "comment_only", "decision_code": "A2", "para": 2,
                                 "external_comment": "נבקש לבחון את הדין החל."}])
    p, out = _apply(received, dec)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "Traceback" not in p.stderr


def test_our_edit_next_to_their_revisions_passes_the_gate_and_keeps_theirs(received):
    dec = _decisions(received, [
        {"id": "D1", "op": "replace_span", "decision_code": "R2", "para": 2, "old": "הישראלי",
         "new": "הישראלי, וסמכות השיפוט תהיה בתל אביב",
         "external_comment": "נבקש לקבוע מקום שיפוט מוסכם, כדי למנוע מחלוקת עתידית."},
        {"id": "D2", "op": "comment_only", "decision_code": "A2", "para": 0,
         "external_comment": "מקובל עלינו להוסיף את רמת הזמינות."}])
    p, out = _apply(received, dec)
    assert p.returncode == 0, p.stdout + p.stderr
    root = etree.fromstring(dt.read_package(str(out))["word/document.xml"])
    rroot = etree.fromstring(dt.read_package(str(received["draft"]))["word/document.xml"])
    assert dt.reject_ours_view(root, US) == [dt.para_text(x) for x in dt.body_paragraphs(rroot)]
    theirs = lambda x: Counter(k for k, a in re.findall(r'<w:(ins|del) [^>]*w:author="([^"]*)"', x) if a == THEM)
    assert theirs(zipfile.ZipFile(out).read("word/document.xml").decode()) == \
        theirs(zipfile.ZipFile(received["draft"]).read("word/document.xml").decode())
    g = subprocess.run([sys.executable, "-B", str(ORCH / "qa_gate.py"), "--mode", "work", "--work", str(out),
                        "--received", str(received["draft"]), "--profile", str(received["profile"]),
                        "--decisions", str(dec), "--expected-accept", str(out).replace(".docx", ".expected.json")],
                       capture_output=True, text=True)
    assert g.returncode == 0, g.stdout
    assert "PKG_AUTHOR" not in g.stdout and "INT_HEADER_MISSING" not in g.stdout and "RT_REJECT" not in g.stdout


def test_a_round_trip_failure_is_printed_and_not_a_crash(received, monkeypatch, capsys):
    import apply_redlines as A
    monkeypatch.setattr(dt.TrackedDocx, "verify_roundtrip", lambda self: [("reject", 0, "a", "b")])
    dec = _decisions(received, [{"id": "D1", "op": "comment_only", "decision_code": "A2", "para": 2,
                                 "external_comment": "נבקש לבחון את הדין החל."}])
    rc = A.main(["--draft", str(received["draft"]), "--decisions", str(dec), "--profile", str(received["profile"]),
                 "--out", str(received["dir"] / "w2.docx")])
    assert "בדיקת הלוך ושוב: ('reject', 0, 'a', 'b')" in capsys.readouterr().out
    assert rc == 3


# ---------------------------------------------------------------- סימון בתוך פסקה עם שינויים פתוחים שלהם
def _revs(path):
    x = zipfile.ZipFile(path).read("word/document.xml").decode()
    return [(k, a, t) for k, a, t in re.findall(
        r'<w:(ins|del) [^>]*w:author="([^"]*)"[^>]*>.*?<w:(?:t|delText)[^>]*>([^<]*)<', x, re.S)]


def _gate(r, out, dec):
    return subprocess.run([sys.executable, "-B", str(ORCH / "qa_gate.py"), "--mode", "work", "--work", str(out),
                           "--received", str(r["draft"]), "--profile", str(r["profile"]), "--decisions", str(dec),
                           "--expected-accept", str(out).replace(".docx", ".expected.json")],
                          capture_output=True, text=True)


@pytest.mark.parametrize("mode,old,deleted", [("reject", "30", "30"), ("accept", "90", "90")])
def test_we_answer_inside_their_change(received, mode, old, deleted):
    """הם שינו 30 ל-90, ואנחנו מציעים 45: דוחים את שלהם ומסמנים מול 30, או מקבלים ומסמנים מעל 90."""
    dec = _decisions(received, [{"id": "D1", "op": "replace_span", "decision_code": "R2", "para": 1, "old": old,
                                 "new": "45", "their_changes": mode,
                                 "external_comment": "הצענו שוטף + 45 ימים, כדי לאזן בין שני הצדדים."}])
    p, out = _apply(received, dec)
    assert p.returncode == 0, p.stdout + p.stderr
    revs = _revs(out)
    assert ("del", US.replace('"', "&quot;"), deleted) in revs and ("ins", US.replace('"', "&quot;"), "45") in revs
    assert not [r for r in revs if r[1] == THEM and r[2] in ("30", "90")]      # השינוי שלהם בפסקה הוכרע
    assert any(r[1] == THEM for r in revs)                                      # ושינוי שלהם בפסקה אחרת נשאר
    root = etree.fromstring(dt.read_package(str(out))["word/document.xml"])
    assert dt.paragraph_views(root, "accept")[1] == "2. התשלום יבוצע בתנאי שוטף + 45 ימים."
    assert _gate(received, out, dec).returncode == 0


def test_by_default_a_counter_rejects_theirs_and_a_comment_keeps_it(received):
    sys.path.insert(0, str(LIB))
    assert dt.their_changes_mode({"op": "replace_span", "decision_code": "R2"}) == "reject"
    assert dt.their_changes_mode({"op": "comment_only", "decision_code": "A2"}) == "keep"
    assert dt.their_changes_mode({"op": "accept", "decision_code": "A1"}) == "accept"
    assert dt.their_changes_mode({"op": "replace", "decision_code": "R1", "their_changes": "accept"}) == "accept"


def test_old_written_against_their_wording_is_explained_and_nothing_is_applied(received):
    dec = _decisions(received, [{"id": "D1", "op": "replace_span", "decision_code": "R2", "para": 1, "old": "90",
                                 "new": "45", "external_comment": "הצענו שוטף + 45 ימים."}])
    p, out = _apply(received, dec)
    assert p.returncode == 3 and "their_changes: accept" in p.stdout
    assert _revs(out) == _revs(received["draft"])        # שום דבר לא הוחל, גם לא דחיית השינוי שלהם
