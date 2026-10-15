# -*- coding: utf-8 -*-
"""בדיקות ל-`approval_sheet.py` ול-`ingest_approval.py`, מקצה לקצה.

המסלול: הפקת הגיליון, חתימה עליו (בעזר של ענבל, שמסמן את התיבות כמו
שהיועצת המשפטית מסמנת), קליטה, ואז בדיקה **שכל השכבות זזו יחד**.

`playbook-schema.md` אומר על `playbook_status`: "נגזר בקוד, ולעולם אינו
נכתב ידנית", ו"אחרי כל קליטה הערך ו-`status_label` נכתבים מחדש באותה
פונקציה לכל השכבות". שש שכבות שנכתבות ביד הן שש שכבות שייסתרו זו את זו,
וזה כבר קרה בסבב 2: המודל אמר "מדיניות מאושרת" בעוד התאים נשארו
מהרשומה המדומה, השאלות המכריעות נשארו פתוחות וה-handoff נשאר Draft.
הבדיקות כאן הן על זה בדיוק: המודל, הגרעין והאינדקס אחרי הקליטה, ולא
רק מה שהודפס.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPTS = (PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts")
SHEET = SCRIPTS / "approval_sheet.py"
INGEST = SCRIPTS / "ingest_approval.py"

sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
pytest.importorskip("docx")

import pb_helpers as H  # noqa: E402

SIGNER = ("דנה לוי", "יועצת משפטית ראשית", "14.10.2026")
SIGNERS = {"green": SIGNER, "yellow": SIGNER, "red": SIGNER}


def _run(script, args):
    return subprocess.run([sys.executable, str(script)] + [str(x) for x in args],
                          capture_output=True, text=True, cwd=str(script.parent))


@pytest.fixture
def built(tmp_path):
    """מודל, גרעין ואינדקס על הדיסק, והגיליון שהופק מהם."""
    model = H.round3_model()
    paths = {"model": tmp_path / "playbook-model.json",
             "core": tmp_path / "playbook-core.json",
             "index": tmp_path / "index.json"}
    paths["model"].write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
    paths["core"].write_text(json.dumps({"rules": []}, ensure_ascii=False), encoding="utf-8")
    paths["index"].write_text(json.dumps({"playbooks": [{
        "core_path": "playbook-core.json",
        "family_code": model.get("family_code") or model.get("family_id"),
        "company_role_code": model.get("company_role_code") or model.get("company_role"),
        "language": "he"}]}, ensure_ascii=False), encoding="utf-8")

    out_dir = tmp_path / "גיליונות"
    r = _run(SHEET, ["--model", paths["model"], "--out-dir", out_dir,
                     "--company", "חברת הדוגמה", "--token-uid", "aaaabbbbcccc"])
    assert r.returncode == 0, r.stdout + r.stderr
    sheet = next(out_dir.glob("*.docx"))
    manifest = out_dir / "approval-sheet-manifest.json"
    assert manifest.exists(), r.stdout
    return {"paths": paths, "sheet": sheet, "manifest": manifest,
            "model": model, "dir": tmp_path}


def _sign(built, tmp_path, **kw):
    """חותם כמו שהיועצת חותמת: כל התיבות שהגיליון מבקש, מהמניפסט עצמו.

    התגיות אינן מומצאות כאן. המניפסט מחזיק את התגית של כל אפשרות בכל
    שאלה ושל כל הנחה, ולכן בחירה והנחה נגזרות ממנו ולא מרשימה קבועה
    שתתיישן עם המודל.
    """
    signed = tmp_path / "חתום.docx"
    man = json.loads(built["manifest"].read_text(encoding="utf-8"))
    choices = kw.pop("choices", None)
    if choices is None:
        choices = [q["options"][0]["tag"] for q in (man.get("questions") or {}).values()
                   if q.get("options")]
    assumptions = kw.pop("assumptions", None)
    if assumptions is None:
        assumptions = [t for c in (man.get("cells") or {}).values()
                       for t in (c.get("assumptions") or [])]
    legal = kw.pop("legal_by", None)
    if legal is None:
        legal = {rid: ("עו\"ד דנה לוי", "13.10.2026")
                 for rid in sorted({k.split("|")[0] for k, c in (man.get("cells") or {}).items()
                                    if c.get("legal_review")})}
    H.sign_sheet(str(built["sheet"]), str(signed), SIGNERS, choices=choices,
                 assumptions=assumptions, legal_by=legal,
                 remove_areo_comments=True, **kw)
    return signed


def _ingest(built, signed, tmp_path, extra=()):
    p = built["paths"]
    args = ["--signed", signed, "--manifest", built["manifest"],
            "--model", p["model"], "--core", p["core"], "--index", p["index"],
            "--records", tmp_path / "אישורים", "--today", "2026-10-14",
            "--received-via", "user_upload",
            "--upload-ref", str(signed)] + list(extra)
    return _run(INGEST, args)


def test_the_sheet_and_its_manifest_are_produced_together(built):
    """מניפסט חסר הוא גיליון שלא ניתן לקלוט, ולכן הוא אינו אופציונלי."""
    man = json.loads(built["manifest"].read_text(encoding="utf-8"))
    assert man["token"].endswith("aaaabbbbcccc")
    assert man["rows"] and man["cells"] and man["issued_sha256"]


def test_a_signed_sheet_moves_every_layer_together(built, tmp_path):
    signed = _sign(built, tmp_path)
    r = _ingest(built, signed, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr

    p = built["paths"]
    model = json.loads(p["model"].read_text(encoding="utf-8"))
    core = json.loads(p["core"].read_text(encoding="utf-8"))
    entry = json.loads(p["index"].read_text(encoding="utf-8"))["playbooks"][0]

    label = model["status_label"]
    assert model["playbook_status"] in ("Approved", "PartiallyApproved")
    # אותה תווית מילה במילה בכל שכבה: זו כל הנקודה
    assert core.get("status_label") == label, (core.get("status_label"), label)
    assert entry.get("status_label") == label, (entry.get("status_label"), label)
    assert label in r.stdout
    assert model["approval_records"], "לא נרשמה רשומת אישור במודל"
    assert "presentation_label" not in json.dumps(model, ensure_ascii=False)


def test_the_decisive_questions_are_closed_by_the_sheet(built, tmp_path):
    """שאלה שהיועצת ענתה עליה בגיליון אינה נשארת 'פתוחה' במודל."""
    signed = _sign(built, tmp_path)
    r = _ingest(built, signed, tmp_path)
    assert r.returncode == 0, r.stdout + r.stderr
    model = json.loads(built["paths"]["model"].read_text(encoding="utf-8"))
    for q in model.get("validation_queue") or ():
        if q.get("answered"):
            assert q["status"] == "closed"
            assert q.get("answer_verbatim") in (q.get("options") or [])
            assert q.get("answered_via"), q


def test_an_ingest_without_evidence_is_marked_simulated(built, tmp_path):
    """בלי ראיה אין אישור אמיתי, וזה נאמר במקום להיבלע."""
    signed = _sign(built, tmp_path)
    p = built["paths"]
    r = _run(INGEST, ["--signed", signed, "--manifest", built["manifest"],
                      "--model", p["model"], "--core", p["core"],
                      "--records", tmp_path / "אישורים", "--today", "2026-10-14"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert "simulated" in r.stdout


def test_a_sheet_from_another_run_is_refused(built, tmp_path):
    """המניפסט הוא מה שקושר את העותק החתום להפקה. אחר אינו נקלט."""
    signed = _sign(built, tmp_path)
    other = tmp_path / "manifest-אחר.json"
    man = json.loads(built["manifest"].read_text(encoding="utf-8"))
    man["token"] = "ISS-0001|family|ffffffffffff"
    other.write_text(json.dumps(man, ensure_ascii=False), encoding="utf-8")
    r = _run(INGEST, ["--signed", signed, "--manifest", other,
                      "--model", built["paths"]["model"],
                      "--records", tmp_path / "אישורים"])
    assert r.returncode == 3, r.stdout + r.stderr
    assert "הפקה אחרת" in r.stdout


def test_superseding_a_record_requires_a_reason(built, tmp_path):
    r = _run(INGEST, ["--signed", built["sheet"], "--manifest", built["manifest"],
                      "--model", built["paths"]["model"],
                      "--records", tmp_path / "אישורים", "--supersedes", "APR-0001"])
    assert r.returncode == 2, r.stdout + r.stderr
    assert "--reason" in r.stdout


def test_an_unsigned_sheet_changes_nothing(built, tmp_path):
    """גיליון שלא נחתם אינו קליטה, והמודל נשאר כפי שהיה."""
    before = built["paths"]["model"].read_text(encoding="utf-8")
    r = _run(INGEST, ["--signed", built["sheet"], "--manifest", built["manifest"],
                      "--model", built["paths"]["model"],
                      "--records", tmp_path / "אישורים"])
    assert r.returncode == 3, r.stdout + r.stderr
    assert built["paths"]["model"].read_text(encoding="utf-8") == before

def test_a_free_text_evidence_channel_is_rejected_by_the_interface(built, tmp_path):
    """תיאור במילים היה הופך כל אישור ל-simulated, ואת הפלייבוק ל-Draft.

    זה קרה בכתיבת הבדיקה הזאת: חתימה מלאה ותקינה נתנה Draft, כי
    `received_via` היה משפט בעברית ולא אחד משני הקודים. עכשיו הממשק
    פוסל את זה, במקום להזהיר ולהמשיך.
    """
    signed = _sign(built, tmp_path)
    p = built["paths"]
    r = _run(INGEST, ["--signed", signed, "--manifest", built["manifest"],
                      "--model", p["model"], "--records", tmp_path / "אישורים",
                      "--received-via", "דוא\"ל מהיועצת המשפטית"])
    assert r.returncode == 2, r.stdout + r.stderr
    assert "user_upload" in r.stderr + r.stdout
    assert json.loads(p["model"].read_text(encoding="utf-8"))["playbook_status"] == "Draft"
