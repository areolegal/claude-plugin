# -*- coding: utf-8 -*-
"""בדיקות לפנקס העסקה, `negotiation_state.py`.

הפנקס הוא הזיכרון של המשא ומתן בין סבב לסבב. הבדיקות כאן על מה שאסור
שיקרה בו, כי כל אחד מאלה עובר בשקט לסבבים הבאים:

* **ויתור שנשכח.** ויתור מסבב 1 חייב להיות בפנקס גם אחרי סבב 2, אחרת
  בסבב 3 מוותרים עליו שוב.
* **היסטוריה שנדרסה.** לפני שהסבב החדש נכתב, הסבב הקודם נשמר כ-
  `negotiation_state_round_<N>.json`.
* **מסמך שנשלח ולא נרשם.** טביעת האצבע של מה שנשלח היא מה שמזהה אותו
  כשהוא חוזר, ולכן היא נרשמת, פעם אחת.
* **קובץ פגום במקום הקובץ החי.** קובץ שאינו עובר את הבדיקה נשמר בצד, והחי
  נשאר כמו שהיה.
* **הכרעת משתמש** נרשמת בקובץ ובסעיף שהיא חלה עליו, ואין מצב עשירי.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPT = (PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator"
          / "scripts" / "negotiation_state.py")
FX = LIB / "tests" / "fixtures" / "orchestrator"


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT)] + [str(a) for a in args],
                          capture_output=True, text=True, cwd=str(SCRIPT.parent))


def _state(deal):
    return json.loads((deal / "negotiation_state.json").read_text(encoding="utf-8"))


@pytest.fixture
def deal(tmp_path):
    d = tmp_path / "Areo-נתונים" / "transactions" / "deal_nda_2026-10-15"
    d.mkdir(parents=True)
    (d / "decisions_round_1.json").write_bytes((FX / "c1r3_decisions_as_sent.json").read_bytes())
    (d / "decisions_round_2.json").write_bytes((FX / "c1r3_decisions_corrected.json").read_bytes())
    (d / "תגובת החברה - סבב 1 - למשלוח.docx").write_bytes(b"PK round one")
    (d / "טיוטה מהצד שכנגד - סבב 2.docx").write_bytes(b"PK their reply")
    (d / "ויתורים.json").write_text(json.dumps([{
        "topic": "תקופת סודיות", "clause_ref": "D02", "tier": "deliberate_concession",
        "user_decision": {"answer_kind": "explicit", "answer": "מסכימים לשלוש שנים"}}],
        ensure_ascii=False), encoding="utf-8")
    return d


def _round1(deal):
    return _run("write", "--deal", deal, "--decisions", deal / "decisions_round_1.json",
                "--counterparty", "הצד השני בע\"מ", "--contract-type", "הסכם סודיות",
                "--concessions", deal / "ויתורים.json",
                "--produced", "send=תגובת החברה - סבב 1 - למשלוח.docx",
                "--sent", "תגובת החברה - סבב 1 - למשלוח.docx")


def test_round_one_is_written_and_valid(deal):
    r = _round1(deal)
    assert r.returncode == 0, r.stdout + r.stderr
    st = _state(deal)
    assert st["meta"]["round_number"] == 1 and st["meta"]["round_stage"] == "opening"
    assert st["clauses"] and st["coverage_index"]
    assert len(st["meta"]["sent_documents"]) == 1
    assert st["produced_documents"][0]["path"].endswith("למשלוח.docx")
    assert _run("check", "--deal", deal).returncode == 0


def test_round_two_keeps_history_and_everything_that_accumulates(deal):
    assert _round1(deal).returncode == 0
    r = _run("write", "--deal", deal, "--decisions", deal / "decisions_round_2.json",
             "--received", "טיוטה מהצד שכנגד - סבב 2.docx")
    assert r.returncode == 0, r.stdout + r.stderr
    st = _state(deal)
    assert st["meta"]["round_number"] == 2 and st["meta"]["round_stage"] == "response"
    # הוויתור מסבב 1 עדיין בפנקס, ולא יינתן שוב
    assert [c["topic"] for c in st["deliberate_concessions"]] == ["תקופת סודיות"]
    # מה שנשלח בסבב 1 נשאר רשום, ומה שהתקבל בסבב 2 נוסף
    assert len(st["meta"]["sent_documents"]) == 1
    assert len(st["meta"]["received_documents"]) == 1
    assert st["meta"]["counterparty_name"] == "הצד השני בע\"מ"
    # הסבב הקודם נשמר לפני שהקובץ החי השתנה
    hist = deal / "negotiation_state_round_1.json"
    assert hist.exists()
    assert json.loads(hist.read_text(encoding="utf-8"))["meta"]["round_number"] == 1


def test_running_the_same_round_again_does_not_overwrite_the_history(deal):
    assert _round1(deal).returncode == 0
    args = ("write", "--deal", deal, "--decisions", deal / "decisions_round_2.json")
    assert _run(*args).returncode == 0
    first = (deal / "negotiation_state_round_1.json").read_text(encoding="utf-8")
    assert _run(*args, "--round", "2").returncode == 0
    assert (deal / "negotiation_state_round_1.json").read_text(encoding="utf-8") == first
    assert not (deal / "negotiation_state_round_2.json").exists()


def test_a_sent_document_is_recorded_once(deal):
    assert _round1(deal).returncode == 0
    r = _run("write", "--deal", deal, "--round", "1",
             "--sent", "תגובת החברה - סבב 1 - למשלוח.docx")
    assert r.returncode == 0, r.stdout
    assert len(_state(deal)["meta"]["sent_documents"]) == 1


def test_a_round_cannot_go_backwards(deal):
    assert _round1(deal).returncode == 0
    assert _run("write", "--deal", deal, "--decisions", deal / "decisions_round_2.json").returncode == 0
    r = _run("write", "--deal", deal, "--round", "1")
    assert r.returncode == 2
    assert "לאחור" in r.stdout


def test_a_user_decision_lands_on_the_file_and_on_the_clause(deal):
    assert _round1(deal).returncode == 0
    cid = _state(deal)["clauses"][1]["clause_id"]
    r = _run("decide", "--deal", deal, "--id", "Q-07", "--situation", "2",
             "--answer", "מאשרים לחצות את הקו האדום בעסקה הזאת", "--answer-kind", "explicit",
             "--applies-to", cid)
    assert r.returncode == 0, r.stdout + r.stderr
    st = _state(deal)
    assert st["user_decisions"][-1]["outcome"] == "user_decided"
    clause = next(c for c in st["clauses"] if c["clause_id"] == cid)
    assert clause["user_decision"]["question_id"] == "Q-07"


def test_there_is_no_tenth_situation(deal):
    assert _round1(deal).returncode == 0
    r = _run("decide", "--deal", deal, "--id", "Q-08", "--situation", "10",
             "--answer", "x", "--answer-kind", "explicit")
    assert r.returncode == 2


def test_an_invalid_state_never_replaces_the_live_file(deal):
    """ויתור שמפנה למזהה כלל ולא לסעיף הוא שגיאה. הקובץ החי אינו נדרס."""
    assert _round1(deal).returncode == 0
    before = (deal / "negotiation_state.json").read_text(encoding="utf-8")
    (deal / "ויתור-פגום.json").write_text(json.dumps([{
        "topic": "אחריות", "clause_ref": "R-04",
        "user_decision": {"answer_kind": "explicit"}}], ensure_ascii=False), encoding="utf-8")
    r = _run("write", "--deal", deal, "--round", "1", "--concessions", deal / "ויתור-פגום.json")
    assert r.returncode == 3, r.stdout
    assert "STATE_CLAUSE_REF" in r.stdout
    assert (deal / "negotiation_state.json").read_text(encoding="utf-8") == before
    assert (deal / "negotiation_state.rejected.json").exists()


def test_an_old_format_file_is_kept_and_converted(deal):
    old = {"meta": {"round_stage": "stopped_at_A2", "round_number": 1,
                    "generated_at": "2026-10-12T12:42:00+03:00", "last_updated": "2026-10-14T14:17:38",
                    "received_documents": [{"file": "nda.docx", "file_name": "nda.docx",
                                            "received": "12.10.2026"}]},
           "clauses": [], "coverage_index": []}
    (deal / "negotiation_state.json").write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
    # write מסרב לעבוד על קובץ ישן, ואומר מה להריץ
    r = _run("write", "--deal", deal)
    assert r.returncode == 2 and "migrate" in r.stdout
    r = _run("migrate", "--deal", deal)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads((deal / "negotiation_state_legacy.json").read_text(encoding="utf-8")) == old
    st = _state(deal)
    assert st["meta"]["schema_version"] == "4.9" and st["meta"]["round_stage"] == "opening"
    assert _run("check", "--deal", deal).returncode == 0
