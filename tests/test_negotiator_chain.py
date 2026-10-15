# -*- coding: utf-8 -*-
"""הנושא ונותן מקצה לקצה: סימון, שער, עותק למשלוח, פנקס, וכלי הסבב.

עד עכשיו הסימון נעשה במנוע הישן, ששער האיכות פוסל את מה שהוא כותב, ולכן
השרשרת לא יכלה לעבור מקצה לקצה. הבדיקה הראשונה כאן היא בדיוק זה: טיוטה
שהתקבלה וקובץ הכרעות, ובסוף עותק למשלוח שעבר את השער ופנקס עסקה תקין.

ושלושה דברים שהמנוע הישן עשה, וענבל ביקשה להסיר (שינויים 4ד, 5, 9, 10):
* פתיח קבוע בבועה, עם "סעיף X למדיניות שלנו";
* צבע בטקסט;
* קבלה של כל השינויים של הצד שכנגד ומחיקת ההערות שלו.
"""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
S = PLUGIN / "areolegal" / "skills" / "contract-negotiation-orchestrator" / "scripts"
FX = LIB / "tests" / "fixtures" / "orchestrator"

sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
pytest.importorskip("lxml")
pytest.importorskip("docx")

import orch_helpers as H  # noqa: E402
import common.docx_tracked as dt  # noqa: E402


def _run(script, *args):
    return subprocess.run([sys.executable, str(S / script)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(S))


@pytest.fixture
def deal(tmp_path):
    d = tmp_path / "Areo-נתונים" / "transactions" / "deal_c1b_2026-10-15"
    d.mkdir(parents=True)
    (d / "טיוטה שהתקבלה.docx").write_bytes(Path(H.DRAFT).read_bytes())
    (d / "decisions_round_1.json").write_bytes((FX / "c1b_decisions_round3_clean.json").read_bytes())
    # הפרופיל כמו שרכיב ההקמה כותב אותו: השם תחת branding, ולא בשורש
    prof = {k: v for k, v in H.PROFILE.items() if not k.startswith("lawyer_")}
    prof["branding"] = {"lawyer_name": H.PROFILE["lawyer_name"],
                        "lawyer_initials": H.PROFILE.get("lawyer_initials")}
    (d / "profile.json").write_text(json.dumps(prof, ensure_ascii=False), encoding="utf-8")
    return d


def _apply(d):
    return _run("apply_redlines.py", "--draft", d / "טיוטה שהתקבלה.docx",
                "--decisions", d / "decisions_round_1.json",
                "--out", d / "תגובת החברה - סבב 1.docx", "--profile", d / "profile.json")


def test_the_whole_chain_ends_in_a_send_copy_and_a_valid_ledger(deal):
    r = _apply(deal)
    assert r.returncode == 0, r.stdout + r.stderr
    work, exp = deal / "תגובת החברה - סבב 1.docx", deal / "תגובת החברה - סבב 1.expected.json"
    assert work.exists() and exp.exists()
    assert (deal / "תגובת החברה - סבב 1.as_produced.docx").exists()

    common = ["--work", work, "--received", deal / "טיוטה שהתקבלה.docx",
              "--profile", deal / "profile.json", "--expected-accept", exp]
    g = _run("qa_gate.py", "--mode", "work", *common, "--out", deal / "gate-work.json")
    assert g.returncode == 0, g.stdout + g.stderr
    send = deal / "תגובת החברה - סבב 1 - למשלוח.docx"
    g = _run("qa_gate.py", "--mode", "send", *common, "--send", send, "--deal", deal,
             "--out", deal / "gate-send.json")
    assert g.returncode == 0, g.stdout + g.stderr
    assert send.exists()

    w = _run("negotiation_state.py", "write", "--deal", deal,
             "--decisions", deal / "decisions_round_1.json", "--gate", deal / "gate-send.json",
             "--produced", "send=" + send.name, "--sent", send.name,
             "--received", "טיוטה שהתקבלה.docx")
    assert w.returncode == 0, w.stdout + w.stderr
    assert _run("negotiation_state.py", "check", "--deal", deal).returncode == 0


def _xml(path, part="word/document.xml"):
    with zipfile.ZipFile(path) as z:
        return z.read(part).decode("utf-8") if part in z.namelist() else ""


def test_no_fixed_opener_no_policy_reference_and_no_colour(deal):
    assert _apply(deal).returncode == 0
    work = deal / "תגובת החברה - סבב 1.docx"
    comments = _xml(work, "word/comments.xml")
    for banned in ("למדיניות שלנו", "מוסכם בכפוף להערות", "לא מוסכם"):
        assert banned not in comments, banned
    before = _xml(deal / "טיוטה שהתקבלה.docx").count("<w:highlight")
    assert _xml(work).count("<w:highlight") <= before


def test_their_comments_and_changes_stay_in_place(deal):
    received = deal / "טיוטה שהתקבלה.docx"
    theirs = dt.read_comments(str(received))
    assert _apply(deal).returncode == 0
    now = dt.read_comments(str(deal / "תגובת החברה - סבב 1.docx"))
    ids = {c["id"] for c in now}
    assert all(c["id"] in ids for c in theirs), "הערה של הצד שכנגד נמחקה"
    # "דחה הכול" על קובץ העבודה מחזיר בדיוק את מה שהתקבל
    assert dt.paragraph_views(dt.document_root(str(deal / "תגובת החברה - סבב 1.docx")), "reject") == \
        [dt.para_text(p) for p in dt.body_paragraphs(dt.document_root(str(received)))]


def test_track_changes_is_on_in_the_work_file(deal):
    assert _apply(deal).returncode == 0
    assert "trackRevisions" in _xml(deal / "תגובת החברה - סבב 1.docx", "word/settings.xml")


def test_a_decisions_file_that_breaks_the_contract_writes_nothing(deal):
    dec = json.loads((deal / "decisions_round_1.json").read_text(encoding="utf-8"))
    dec["decisions"][0]["op"] = "rewrite_everything"
    bad = deal / "decisions_bad.json"
    bad.write_text(json.dumps(dec, ensure_ascii=False), encoding="utf-8")
    r = _run("apply_redlines.py", "--draft", deal / "טיוטה שהתקבלה.docx", "--decisions", bad,
             "--out", deal / "לא אמור להיווצר.docx", "--profile", deal / "profile.json")
    assert r.returncode == 2, r.stdout
    assert "op לא מוכר" in r.stdout
    assert not (deal / "לא אמור להיווצר.docx").exists()


def test_no_lawyer_name_stops_and_asks(deal):
    (deal / "profile.json").write_text("{}", encoding="utf-8")
    dec = json.loads((deal / "decisions_round_1.json").read_text(encoding="utf-8"))
    dec.pop("author", None)
    (deal / "decisions_round_1.json").write_text(json.dumps(dec, ensure_ascii=False), encoding="utf-8")
    r = _apply(deal)
    assert r.returncode == 2 and "מי חותם" in r.stdout


def test_the_output_never_overwrites_the_received_draft(deal):
    r = _run("apply_redlines.py", "--draft", deal / "טיוטה שהתקבלה.docx",
             "--decisions", deal / "decisions_round_1.json",
             "--out", deal / "טיוטה שהתקבלה.docx", "--profile", deal / "profile.json")
    assert r.returncode == 1 and "סירוב" in r.stdout


# ------------------------------------------------------------------ כלי הסבב
def test_a_question_asked_in_an_earlier_batch_is_not_asked_again(deal, tmp_path):
    assert _apply(deal).returncode == 0
    assert _run("negotiation_state.py", "write", "--deal", deal,
                "--decisions", deal / "decisions_round_1.json").returncode == 0
    items = tmp_path / "items.json"
    items.write_text(json.dumps([
        {"key": "Q-CAP", "text": "תקרת האחריות נמוכה מהקו האדום.", "situation": 2,
         "recommendation": "לא לחצות", "options": ["לא לחצות", "לחצות"], "blocks_sending": True},
        {"key": "components", "text": "להפעיל את מעריך הסיכונים?", "situation": None,
         "options": ["כן", "לא"]}], ensure_ascii=False), encoding="utf-8")
    r = _run("round_tools.py", "questions", "--items", items, "--deal", deal)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "נדרשת הכרעתך (מצב 2, חוסם משלוח" in r.stdout
    again = _run("round_tools.py", "questions", "--items", items, "--deal", deal)
    assert "כבר נשאלה" in again.stdout


def test_there_is_no_tenth_situation(tmp_path):
    items = tmp_path / "items.json"
    items.write_text(json.dumps([{"key": "x", "text": "y", "situation": 10}]), encoding="utf-8")
    r = _run("round_tools.py", "questions", "--items", items)
    assert r.returncode == 2 and "מצב עשירי" in r.stdout


def test_the_review_table_has_no_approval_chain(deal, tmp_path):
    dec = tmp_path / "dec.json"
    dec.write_text(json.dumps({"decisions": [
        {"id": "D1", "summary": "תקרה בגובה התמורה", "source": "playbook"},
        {"id": "D2", "summary": "שיפוי בלי תקרה", "crosses_red_line": True,
         "user_decision": {"answer_kind": "explicit", "answer": "מאשרים בעסקה הזאת"}},
        {"id": "D3", "summary": "סנקציות", "situation": 8}]}, ensure_ascii=False), encoding="utf-8")
    r = _run("round_tools.py", "review", "--decisions", dec)
    assert r.returncode == 0, r.stdout
    assert "| סעיף | מה הוכרע | תווית מקור |" in r.stdout
    assert "חוצה קו אדום: הכרעתך" in r.stdout
    assert "סנקציות" not in r.stdout, "נושא ציות אינו בטבלה"


def test_signing_is_blocked_while_anything_is_open(deal):
    assert _apply(deal).returncode == 0
    exp = deal / "תגובת החברה - סבב 1.expected.json"
    g = _run("qa_gate.py", "--mode", "work", "--work", deal / "תגובת החברה - סבב 1.docx",
             "--received", deal / "טיוטה שהתקבלה.docx", "--profile", deal / "profile.json",
             "--expected-accept", exp, "--out", deal / "gate.json")
    assert g.returncode == 0
    r = _run("round_tools.py", "signing", "--gate", deal / "gate.json",
             "--profile", deal / "profile.json")
    # בפרופיל של הבדיקה אין שם רשום של החברה, ולכן הרשימה אינה עוברת
    assert r.returncode == 3, r.stdout
    assert "registered_legal_name" in r.stdout and "אינו מופק" in r.stdout


def test_proportionality_asks_when_there_are_more_asks_than_the_fight_list(tmp_path):
    dec = tmp_path / "dec.json"
    dec.write_text(json.dumps({"decisions": [
        {"id": "D%d" % i, "decision_code": "R2", "importance": "low"} for i in range(6)] + [
        {"id": "H1", "decision_code": "R1", "structural": True}]}), encoding="utf-8")
    r = _run("round_tools.py", "proportionality", "--decisions", dec, "--fight-list", "3",
             "--value-text", "50,000 ש\"ח")
    assert r.returncode == 3, r.stdout
    assert "6 דרישות" in r.stdout, "כותרת אינה נספרת"
    assert "נדרשת הכרעתך (מצב 4)" in r.stdout
    assert len(re.findall(r"D\d", r.stdout.split("ויתורים מוצעים:")[1].split("\n")[0])) == 3


def test_approval_chain_wording_outside_the_quote_is_still_caught(tmp_path):
    """ההחרגה היא לציטוט של המשתמש בלבד. "טעון אישור" בתוכן ההכרעה נתפס."""
    dec = tmp_path / "dec.json"
    dec.write_text(json.dumps({"decisions": [
        {"id": "D1", "summary": "שיפוי בלי תקרה, טעון אישור מנכ\"ל", "source": "playbook"}]},
        ensure_ascii=False), encoding="utf-8")
    r = _run("round_tools.py", "review", "--decisions", dec)
    assert r.returncode == 3 and "approval_chain_wording" in r.stdout


def test_file_names_follow_the_rule_and_never_overwrite(deal):
    """`<סוג> - <חברה> - סבב N - <תאריך>`, עם " - פנימי" ו-" - כפי שהופק".

    בנתיב ארוך הספרייה משמיטה קודם את שם החברה, כדי להישאר בתוך 230 תווים
    (`common/paths.safe_out_paths`). תיקיית הבדיקה ארוכה, ולכן השמות נקראים
    מהפלט ולא מונחים מראש."""
    args = ("apply_redlines.py", "--draft", deal / "טיוטה שהתקבלה.docx",
            "--decisions", deal / "decisions_round_1.json", "--profile", deal / "profile.json",
            "--deal", deal, "--agreement-type", "הסכם שירותים", "--company", "חברת הדוגמה",
            "--round", "1", "--date", "15.10.2026")
    r = _run(*args)
    assert r.returncode == 0, r.stdout + r.stderr
    work = Path(re.search(r"קובץ העבודה: (.+)", r.stdout).group(1).strip())
    send = re.search(r"--send\): (.+)", r.stdout).group(1).strip()
    assert work.exists() and len(str(work)) <= 230
    assert work.name.startswith("הסכם שירותים") and work.name.endswith("סבב 1 - 15.10.2026 - פנימי.docx")
    assert send.endswith("סבב 1 - 15.10.2026.docx")
    assert Path(str(work).replace(" - פנימי.docx", " - כפי שהופק.docx")).exists()
    again = _run(*args)
    assert again.returncode == 0, again.stdout
    assert Path(str(work).replace(".docx", " (2).docx")).exists(), "קובץ קיים אינו נדרס"


def test_an_existing_send_copy_is_never_overwritten(deal):
    assert _apply(deal).returncode == 0
    send = deal / "למשלוח.docx"
    send.write_bytes(b"PK an earlier send copy")
    exp = deal / "תגובת החברה - סבב 1.expected.json"
    g = _run("qa_gate.py", "--mode", "send", "--work", deal / "תגובת החברה - סבב 1.docx",
             "--received", deal / "טיוטה שהתקבלה.docx", "--profile", deal / "profile.json",
             "--expected-accept", exp, "--send", send)
    assert g.returncode == 0, g.stdout + g.stderr
    assert send.read_bytes() == b"PK an earlier send copy"
    assert (deal / "למשלוח (2).docx").exists()


def _state_with_signing(d, passed):
    sys.path.insert(0, str(LIB))
    from orchestrator import state_builder as SB
    st = SB.build_state("deal_c1b", 1)
    st["signing_checklist"] = {"checks": [], "passed": passed}
    (d / "negotiation_state.json").write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def test_the_clean_copy_waits_for_the_signing_checklist(deal):
    assert _apply(deal).returncode == 0
    _state_with_signing(deal, False)
    out = deal / "לחתימה.docx"
    r = _run("round_tools.py", "clean-copy", "--agreed", deal / "תגובת החברה - סבב 1.docx",
             "--out", out, "--deal", deal)
    assert r.returncode == 3, r.stdout + r.stderr
    assert not out.exists()


def test_the_clean_copy_is_the_agreed_text_with_no_marks_and_no_comments(deal):
    assert _apply(deal).returncode == 0
    _state_with_signing(deal, True)
    agreed = deal / "תגובת החברה - סבב 1.docx"
    out = deal / "לחתימה.docx"
    r = _run("round_tools.py", "clean-copy", "--agreed", agreed, "--out", out, "--deal", deal)
    assert r.returncode == 0, r.stdout + r.stderr
    assert dt.received_paragraphs(str(out)) == dt.accept_all(str(agreed))
    parts = dt.read_package(str(out))
    assert not [n for n in parts if n.startswith("word/comments")]
    body = parts["word/document.xml"].decode("utf-8")
    for tag in ("<w:ins ", "<w:del ", "commentReference", "commentRangeStart"):
        assert tag not in body, tag
    assert "trackRevisions" not in parts["word/settings.xml"].decode("utf-8")
    headers = "".join(parts[n].decode("utf-8", "ignore") for n in parts if n.startswith("word/header"))
    assert dt.INTERNAL_HEADER_TEXT not in headers
    st = json.loads((deal / "negotiation_state.json").read_text(encoding="utf-8"))
    assert st["signing_checklist"]["clean_copy_path"].endswith("לחתימה.docx")
    assert len(st["signing_checklist"]["agreed_version_sha256"]) == 64
