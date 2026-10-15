# -*- coding: utf-8 -*-
"""בדיקות ל-`verify_playbook_docx.py`, בדיקת הקבלה של ה-Word.

`word-export-spec.md`: "מסמך שנכשל באחת הבדיקות אינו נמסר", והמפרט
מסיים ב"**אל תכתוב שהמסמך נבדק כשהבדיקה לא רצה**". לכן נבדקים כאן שני
דברים נפרדים: שכל בדיקה **נושכת** כשיש פגם, ושבדיקה שלא רצה מדווחת
כדילוג עם סיבה ואינה נספרת כהצלחה.

המסמך שנבנה כאן הוא העזר של ענבל (`pb_helpers.playbook_docx`), שהוא
מסמך מינימלי לבדיקות ולא פלייבוק שלם. לכן הבדיקות כאן הן על הממצאים
עצמם, ולא על "המסמך הזה עובר": מסמך בדיקה שעובר את בדיקת הקבלה היה
אומר שהבדיקה אינה בודקת.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPT = (PLUGIN / "areolegal" / "skills" / "contract-playbook-builder"
          / "scripts" / "verify_playbook_docx.py")

sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
pytest.importorskip("docx")
pytest.importorskip("lxml")

import pb_helpers as H  # noqa: E402
from playbook import status as S  # noqa: E402


@pytest.fixture
def built(tmp_path):
    model = H.round3_model()
    st = S.derive_status(model)
    docx = tmp_path / "פלייבוק.docx"
    H.playbook_docx(str(docx), model, st["label"])
    mp = tmp_path / "playbook-model.json"
    mp.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    return {"docx": docx, "model": mp, "data": model, "status": st}


def _run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(SCRIPT.parent))


def _check(stdout, num):
    """השורה של בדיקה אחת, ומה שמודפס תחתיה."""
    lines = stdout.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("%d. " % num):
            rest = []
            for nxt in lines[i + 1:]:
                if nxt[:2].strip().rstrip(".").isdigit() or not nxt.strip():
                    break
                rest.append(nxt.strip())
            return line, rest
    raise AssertionError("בדיקה %d אינה בפלט:\n%s" % (num, stdout))


def test_every_one_of_the_nine_checks_is_reported(built):
    r = _run(["--docx", built["docx"], "--model", built["model"],
              "--run-date", "2026-10-15"])
    for n in range(1, 10):
        line, _ = _check(r.stdout, n)
        assert ("עבר" in line) or ("נכשל" in line) or ("דולגה" in line), line


def test_a_failing_document_is_not_delivered(built):
    """קוד יציאה 3, ואמירה מפורשת שאין למסור."""
    r = _run(["--docx", built["docx"], "--model", built["model"],
              "--run-date", "2026-10-15"])
    assert r.returncode == 3, r.stdout
    assert "אינו נמסר" in r.stdout


def test_the_direction_check_passes_on_a_document_built_with_the_rtl_helper(built):
    """בדיקה 1 היא audit_docx, והעזר בונה מסמך RTL תקין. היא לא אמורה להרעיש."""
    r = _run(["--docx", built["docx"], "--model", built["model"],
              "--run-date", "2026-10-15"])
    line, _ = _check(r.stdout, 1)
    assert "עבר" in line, line


def test_a_placeholder_in_the_document_is_caught(built, tmp_path):
    """מסמך שנוסח בו "טרם נכתב" אינו מסמך שנמסר."""
    from docx import Document

    from common import rtl
    docx = tmp_path / "עם-מחזיק-מקום.docx"
    doc = Document(str(built["docx"]))
    rtl.add_paragraph(doc, "העמדה בסעיף הזה טרם נכתב", size=11)
    rtl.enforce_document(doc, author="EXAMPLECO", title="פלייבוק")
    doc.save(str(docx))
    r = _run(["--docx", docx, "--model", built["model"], "--run-date", "2026-10-15"])
    line, rest = _check(r.stdout, 2)
    assert "נכשל" in line
    assert any("טרם נכתב" in x for x in rest), rest


def test_the_missing_brief_chapter_is_caught(built):
    """בדיקה 8: ב"העמדות בקצרה" יש שורה לכל כלל במודל."""
    r = _run(["--docx", built["docx"], "--model", built["model"],
              "--run-date", "2026-10-15"])
    line, rest = _check(r.stdout, 8)
    assert "נכשל" in line
    assert any("העמדות בקצרה" in x for x in rest), rest


def test_a_skipped_check_says_so_and_is_not_counted_as_passed(built):
    """"אל תכתוב שהמסמך נבדק כשהבדיקה לא רצה"."""
    r = _run(["--docx", built["docx"], "--model", built["model"],
              "--run-date", "2026-10-15"])
    line, _ = _check(r.stdout, 3)
    assert "דולגה" in line and "--artifact" in line
    assert "לא נבדק:" in r.stdout
    summary = [l for l in r.stdout.split("\n") if l.startswith("נבדק:")][0]
    assert "שוויון" not in summary, summary


def test_the_parity_check_runs_when_the_artifact_is_given(built, tmp_path):
    artifact = tmp_path / "סביבה.html"
    H.workspace_html(str(artifact), built["data"], built["status"]["label"])
    r = _run(["--docx", built["docx"], "--model", built["model"],
              "--artifact", artifact, "--run-date", "2026-10-15"])
    line, _ = _check(r.stdout, 3)
    assert "דולגה" not in line or "מטען" in line, line


def test_a_stale_label_in_the_word_is_caught(built, tmp_path):
    """בדיקה 5: התווית מודפסת מילה במילה, וזהה למחושב."""
    docx = tmp_path / "תווית-ישנה.docx"
    H.playbook_docx(str(docx), built["data"], "מדיניות מאושרת, 01.01.2026, בידי אחר, תפקיד")
    r = _run(["--docx", docx, "--model", built["model"], "--run-date", "2026-10-15"])
    line, rest = _check(r.stdout, 5)
    assert "נכשל" in line, (line, rest)


def test_a_missing_input_is_two(built, tmp_path):
    r = _run(["--docx", tmp_path / "אין-כזה.docx", "--model", built["model"]])
    assert r.returncode == 2, r.stdout
    assert "אינו קיים" in r.stdout


def test_the_report_carries_every_check(built, tmp_path):
    out = tmp_path / "קבלה.json"
    r = _run(["--docx", built["docx"], "--model", built["model"],
              "--run-date", "2026-10-15", "--out", out])
    assert r.returncode == 3
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["passed"] is False
    assert [c["check"] for c in data["checks"]] == list(range(1, 10))
