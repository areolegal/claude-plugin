# -*- coding: utf-8 -*-
"""בדיקות ל-`qa_gate.py`: המצבים, קודי היציאה, ומה נשאר בתיקייה.

השער עצמו נבדק אצל ענבל (`lib/tests/test_qa_gate.py`), ואלה 60 בדיקות
על מחלקות הפגמים. מה שנבדק כאן הוא ההתנהגות שהעטיפה אחראית לה, וזו
ההתנהגות שמונעת שליחה של קובץ פגום:

* **קוד היציאה.** כשל בשער אינו תקלה טכנית והוא אינו הצלחה: הוא 3.
  רכיב שרואה 0 ממשיך למסירה, ולכן 0 שאינו אמת הוא הכשל החמור ביותר כאן.
* **מה נשאר בתיקייה.** כשהשער נכשל במצב משלוח, אסור שיישאר בנתיב קובץ
  "למשלוח" — לא חדש ולא ישן. קובץ שנכשל ומחכה בתיקייה הוא קובץ שיישלח.
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


@pytest.fixture(scope="module")
def clean(tmp_path_factory):
    """קובץ עבודה שעובר את השער: ההכרעות הנקיות של סבב 3 על הטיוטה."""
    out = tmp_path_factory.mktemp("gate")
    work = out / "work.docx"
    res = dt.apply_decisions(H.DRAFT, H.load_decisions("c1b_decisions_round3_clean.json"),
                             out_path=str(work))
    assert not res["errors"], res["errors"]
    profile = out / "profile.json"
    profile.write_text(json.dumps(H.PROFILE, ensure_ascii=False), encoding="utf-8")
    expected = out / "expected_accept.json"
    expected.write_text(json.dumps(res["expected_accept"], ensure_ascii=False),
                        encoding="utf-8")
    return {"work": work, "profile": profile, "expected": expected, "dir": out}


def _run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(SCRIPT.parent))


def _base(clean, mode):
    return ["--mode", mode, "--work", clean["work"], "--received", H.DRAFT,
            "--profile", clean["profile"], "--expected-accept", clean["expected"]]


def test_the_work_file_passes_the_work_mode(clean):
    r = _run(_base(clean, "work"))
    assert r.returncode == 0, r.stdout + r.stderr
    assert "תוצאה: עבר" in r.stdout


def test_the_send_copy_is_produced_and_has_no_internal_layer(clean, tmp_path):
    send = tmp_path / "למשלוח.docx"
    r = _run(_base(clean, "send") + ["--send", send])
    assert r.returncode == 0, r.stdout + r.stderr
    assert send.exists(), r.stdout
    parts = dt.read_package(str(send))
    headers = "".join(parts[n].decode("utf-8", "ignore")
                      for n in parts if n.startswith("word/header"))
    assert dt.INTERNAL_HEADER_TEXT not in headers
    internal = [c for c in dt.read_comments(parts)
                if c["author"] == dt.INTERNAL_AUTHOR]
    assert not internal, internal


def test_a_failing_file_exits_three_and_leaves_no_send_copy(clean, tmp_path):
    """הקובץ שנכשל אינו נשאר בתיקייה: קובץ שמחכה הוא קובץ שיישלח."""
    send = tmp_path / "למשלוח.docx"
    # אותו קובץ עבודה, אבל מוצהר כנוסחי יעד אחרים: בדיקת ההלוך ושוב נכשלת
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps(["נוסח שאינו בקובץ"], ensure_ascii=False),
                     encoding="utf-8")
    r = _run(["--mode", "send", "--work", clean["work"], "--received", H.DRAFT,
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
    r = _run(["--mode", "send", "--work", clean["work"], "--received", H.DRAFT,
              "--profile", clean["profile"], "--expected-accept", wrong,
              "--send", send])
    assert r.returncode == 3, r.stdout + r.stderr
    assert not send.exists(), "העותק הישן נשאר בשמו אחרי שהשער נכשל"
    assert list(tmp_path.glob("*לא למשלוח*")), sorted(p.name for p in tmp_path.iterdir())


def test_the_missing_roundtrip_check_is_said_out_loud(clean):
    """בלי נוסחי היעד הבדיקה אינה רצה, וזה נאמר ולא מושתק."""
    r = _run(["--mode", "work", "--work", clean["work"], "--received", H.DRAFT,
              "--profile", clean["profile"]])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "RT_ACCEPT" in r.stdout and "אינה רצה" in r.stdout


def test_a_missing_input_is_two_and_not_a_traceback(clean):
    r = _run(["--mode", "work", "--work", clean["dir"] / "no-such.docx",
              "--received", H.DRAFT, "--profile", clean["profile"]])
    assert r.returncode == 2, r.stdout + r.stderr
    assert "אינו קיים" in r.stdout
    assert "Traceback" not in r.stderr


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
