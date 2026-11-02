# -*- coding: utf-8 -*-
"""בדיקות ל-`qa_gate.py`: המצבים, קודי היציאה, ומה נשאר בתיקייה.

השער עצמו נבדק אצל ענבל (`lib/tests/test_qa_gate.py`), ואלה 60 בדיקות
על מחלקות הפגמים. מה שנבדק כאן הוא ההתנהגות שהעטיפה אחראית לה, וזו
ההתנהגות שמונעת שליחה של קובץ פגום:

* **קוד היציאה.** כשל בשער אינו תקלה טכנית והוא אינו הצלחה: הוא 3.
  רכיב שרואה 0 ממשיך למסירה, ולכן 0 שאינו אמת הוא הכשל החמור ביותר כאן.
* **מה נשאר בתיקייה.** כשהשער נכשל במצב משלוח, אסור שיישאר בנתיב קובץ
  "למשלוח" - לא חדש ולא ישן. קובץ שנכשל ומחכה בתיקייה הוא קובץ שיישלח.
* **הדיווח הוא של השער.** הקודים והניסוחים נדפסים כפי שהם, ואין "עבר"
  כשיש כשלים.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPT = (PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator"
          / "scripts" / "qa_gate.py")

sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
pytest.importorskip("docx")
pytest.importorskip("lxml")

import orch_helpers as H  # noqa: E402
from common import docx_tracked as dt  # noqa: E402

sys.path.insert(0, str(SCRIPT.parent))
from lawyer import lawyer_view  # noqa: E402


BASE = ["הסכם שירותים", "1. הספק יספק את השירותים בהתאם לנספח.", "2. כל צד רשאי לסיים בהתראה של 30 יום."]


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    """קובץ עבודה שעובר את השער בשני המצבים: הכרעה אחת על טיוטה קטנה, עם בועה חיצונית ובועה פנימית.

    מאז 1.23 השער במצב משלוח דורש קובץ מצב עם סעיפים ואת קובץ ההכרעות (STATE_NO_CLAUSES, DEC_FILE_MISSING:
    n6-gate-and-send.md:32, n4c-produce.md:48), ועם קובץ ההכרעות רצות גם בדיקות התוכן (content_checks). הטיוטה של
    C1ב נשארת לבדיקות של הספרייה; כאן נבדקת העטיפה."""
    out = tmp_path_factory.mktemp("gate")
    received = Path(H.small_draft(str(out / "received.docx"), BASE))
    work = out / "work.docx"
    # הסימונים נחתמים בשם שהעטיפה קוראת מהפרופיל, בלי התואר (lawyer.py, split_signer); כך apply_redlines.py חותם
    dec = H.decisions({"id": "D1", "op": "replace_span", "para": 1, "old": "יספק", "new": "יעניק",
                       "decision_code": "R1", "external_comment": "תיקנו את המינוח, כדי שיתאים להגדרות בהסכם.",
                       "internal_comment": "מינוח בלבד; אין שינוי בהיקף השירותים.",
                       "plain_effect": "מינוח", "position_effect": "ללא שינוי"})
    dec["author"] = lawyer_view(H.PROFILE)["lawyer_name"]
    res = dt.apply_decisions(str(received), dec, out_path=str(work))
    assert not res["errors"], res["errors"]
    profile = out / "profile.json"
    profile.write_text(json.dumps(H.PROFILE, ensure_ascii=False), encoding="utf-8")
    expected = out / "expected_accept.json"
    expected.write_text(json.dumps(res["expected_accept"], ensure_ascii=False),
                        encoding="utf-8")
    decisions = out / "decisions.json"
    decisions.write_text(json.dumps(dec, ensure_ascii=False), encoding="utf-8")
    state = out / "negotiation_state.json"
    state.write_text(json.dumps({"clauses": [{"clause_id": d["id"]} for d in dec["decisions"]]},
                                ensure_ascii=False), encoding="utf-8")
    # המאמת העצמאי הוא תנאי למשלוח (VERIFY_MISSING, n9-verify.md): קובץ ממצאים בלי ממצא פתוח
    verify = out / "verify-findings.json"
    import qa_gate as gate_wrapper   # העטיפה עצמה: טביעת האצבע של הנוסח המתקבל שהמאמת קרא (VERIFY_NOT_BOUND)
    verify.write_text(json.dumps({"verifier": "n9", "round": 1, "read": [str(work)], "findings": [],
                                  "work_sha256": gate_wrapper.accepted_fingerprint(str(work))}), encoding="utf-8")
    return {"work": work, "profile": profile, "expected": expected, "dir": out, "decisions": decisions,
            "state": state, "received": received, "verify": verify}


def _run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(SCRIPT.parent))


def _base(clean, mode):
    return ["--mode", mode, "--work", clean["work"], "--received", clean["received"],
            "--profile", clean["profile"], "--expected-accept", clean["expected"],
            "--decisions", clean["decisions"], "--state", clean["state"], "--verify-findings", clean["verify"]]


def test_the_work_file_passes_the_work_mode(clean):
    r = _run(_base(clean, "work"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "תוצאה: עבר" in r.stdout


def test_the_send_copy_is_produced_and_has_no_internal_layer(clean, tmp_path):
    # קובץ העבודה נושא תמיד את השכבה הפנימית (החלטת מוצר 02.11.2026), והעותק למשלוח נקי ממנה
    assert [c for c in dt.read_comments(dt.read_package(str(clean["work"])))
            if c["author"] in dt.INTERNAL_AUTHORS], "בקובץ העבודה אין בועה פנימית"
    send = tmp_path / "למשלוח.docx"
    r = _run(_base(clean, "send") + ["--send", send])
    assert r.returncode == 0, r.stdout + r.stderr
    assert send.exists(), r.stdout
    parts = dt.read_package(str(send))
    headers = "".join(parts[n].decode("utf-8", "ignore")
                      for n in parts if n.startswith("word/header"))
    assert dt.INTERNAL_HEADER_TEXT not in headers
    internal = [c for c in dt.read_comments(parts)
                if c["author"] in dt.INTERNAL_AUTHORS]
    assert not internal, internal


def test_a_failing_file_exits_three_and_leaves_no_send_copy(clean, tmp_path):
    """הקובץ שנכשל אינו נשאר בתיקייה: קובץ שמחכה הוא קובץ שיישלח."""
    send = tmp_path / "למשלוח.docx"
    # אותו קובץ עבודה, אבל מוצהר כנוסחי יעד אחרים: בדיקת ההלוך ושוב נכשלת
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps(["נוסח שאינו בקובץ"], ensure_ascii=False),
                     encoding="utf-8")
    r = _run(["--mode", "send", "--work", clean["work"], "--received", clean["received"],
              "--profile", clean["profile"], "--expected-accept", wrong,
              "--send", send])
    assert r.returncode == 3, r.stdout + r.stderr
    assert "RT_ACCEPT" in r.stdout
    assert "תוצאה: נכשל" in r.stdout
    assert not send.exists(), "קובץ למשלוח נשאר בתיקייה אחרי כשל בשער"
    assert not list(tmp_path.glob("*.tmp.docx")), "הקובץ הזמני לא נמחק"


def test_an_earlier_send_copy_is_renamed_when_the_gate_fails(clean, tmp_path):
    """עותק ישן בנתיב מקבל 'לא למשלוח', ולא נשאר כפי שהוא."""
    send = tmp_path / "למשלוח.docx"
    ok = _run(_base(clean, "send") + ["--send", send])
    assert ok.returncode == 0 and send.exists(), ok.stdout
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps(["נוסח שאינו בקובץ"], ensure_ascii=False),
                     encoding="utf-8")
    r = _run(["--mode", "send", "--work", clean["work"], "--received", clean["received"],
              "--profile", clean["profile"], "--expected-accept", wrong,
              "--send", send])
    assert r.returncode == 3, r.stdout + r.stderr
    assert not send.exists(), "העותק הישן נשאר בשמו אחרי שהשער נכשל"
    assert list(tmp_path.glob("*לא למשלוח*")), sorted(p.name for p in tmp_path.iterdir())


def test_the_missing_roundtrip_check_is_said_out_loud(clean):
    """בלי נוסחי היעד הבדיקה אינה רצה, וזה נאמר ולא מושתק."""
    r = _run(["--mode", "work", "--work", clean["work"], "--received", clean["received"],
              "--profile", clean["profile"]])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RT_ACCEPT" in r.stdout and "אינה רצה" in r.stdout


def test_a_missing_input_is_two_and_not_a_traceback(clean):
    r = _run(["--mode", "work", "--work", clean["dir"] / "no-such.docx",
              "--received", clean["received"], "--profile", clean["profile"]])
    assert r.returncode == 2, r.stdout + r.stderr
    assert "אינו קיים" in r.stdout
    assert "Traceback" not in r.stderr


def test_send_mode_without_state_and_decisions_fails_and_leaves_no_copy(clean, tmp_path):
    """במצב משלוח, בלי קובץ מצב ובלי קובץ ההכרעות: כשל (3), ואין עותק."""
    send = tmp_path / "למשלוח.docx"
    r = _run(["--mode", "send", "--work", clean["work"], "--received", clean["received"],
              "--profile", clean["profile"], "--expected-accept", clean["expected"], "--send", send])
    assert r.returncode == 3, r.stdout + r.stderr
    assert "STATE_NO_CLAUSES" in r.stdout and "DEC_FILE_MISSING" in r.stdout and "VERIFY_MISSING" in r.stdout
    assert not send.exists()


def test_send_mode_without_a_send_path_stops(clean):
    r = _run(_base(clean, "send"))
    assert r.returncode == 2, r.stdout + r.stderr
    assert "--send" in r.stdout


def test_the_report_is_written_and_carries_the_failure_codes(clean, tmp_path):
    out = tmp_path / "gate.json"
    r = _run(_base(clean, "work") + ["--out", out])
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["passed"] and data["mode"] == "work"
    assert "failures" in data and "warnings" in data and data["info"]["lang"]


def test_the_report_is_refused_on_top_of_an_input(clean):
    r = _run(_base(clean, "work") + ["--out", clean["work"]])
    assert r.returncode == 1, r.stdout + r.stderr
    assert "סירוב" in r.stdout
