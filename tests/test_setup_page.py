# -*- coding: utf-8 -*-
"""עמוד ההקמה בשלב הפלייבוק (setup_page.py): העמוד נבנה מהפלייבוק עצמו, וההכרעות שחוזרות ממנו נקלטות דרך תור
האישור הרשמי, אותו תור שהצ'אט עובר בו, ולא במסלול נפרד."""
import json
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
LIB = PLUGIN / "areolegal" / "lib"
SCRIPTS = PLUGIN / "areolegal" / "skills" / "contract-playbook-builder" / "scripts"
PAGE = PLUGIN / "areolegal" / "skills" / "contract-setup-diagnostician" / "assets" / "setup-page.html"
CLI = SCRIPTS / "setup_page.py"

sys.path.insert(0, str(LIB))
sys.path.insert(0, str(LIB / "tests"))
sys.path.insert(0, str(SCRIPTS))

import pb_helpers as H  # noqa: E402
import setup_page as SP  # noqa: E402
from playbook import status as S  # noqa: E402

APPROVER = {"name": "דנה לוי", "role": "יועצת משפטית"}


def _model(tmp_path):
    m = H.round3_model()
    p = tmp_path / "playbook-model.json"
    p.write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
    rec = tmp_path / "אישורים"
    rec.mkdir()
    return m, p, rec


def _init_of(page):
    html = page.read_text(encoding="utf-8")
    assert SP.MARKER not in html
    start = html.index('{"mode": "approve"')
    return json.JSONDecoder().raw_decode(html[start:])[0], html


def test_the_page_lists_only_unapproved_topics_with_their_legal_concern(tmp_path):
    m, p, rec = _model(tmp_path)
    init = SP.build_init(m, str(p), str(rec), APPROVER)
    ids = [x["id"] for x in init["positions"]]
    assert ids and len(ids) == len(set(ids))
    for x in init["positions"]:
        assert x["g"], "כל נושא מוצג עם העמדה המועדפת"
        assert x["legal"] == (x["id"] in init["legal"])
    assert init["approver"] == APPROVER
    assert init["family"] and "(" in init["family"], "כותרת העמוד: סוג ההסכם והצד של החברה"


def test_an_approver_that_is_not_a_full_name_is_not_prefilled(tmp_path):
    m, p, rec = _model(tmp_path)
    assert "approver" not in SP.build_init(m, str(p), str(rec), {"name": "דנה", "role": ""})
    assert "approver" not in SP.build_init(m, str(p), str(rec), {"name": "היועצת המשפטית", "role": ""})


def test_the_page_is_written_from_the_product_asset_and_cannot_close_its_script(tmp_path):
    init = {"mode": "approve", "family": "x", "positions": [{"id": "R1", "t": "</script><b>", "g": "a"}],
            "legal": {}}
    out = tmp_path / "approve.html"
    SP.write_page(str(PAGE), init, str(out))
    got, html = _init_of(out)
    assert got["positions"][0]["t"] == "</script><b>"
    assert "</script><b>" not in html


def test_the_reply_follows_the_page_decisions():
    by_rule = {"R1": {"decision": "approved"}, "R2": {"decision": "change_requested"},
               "R3": {"decision": "approved_after_legal_review"}, "R4": {"decision": "legal_review_later"}}
    batch = {"stage": "batch", "items": [{"n": 1, "rule_id": "R1"}, {"n": 2, "rule_id": "R2"}]}
    assert SP.reply_for(batch, by_rule) == "לאשר הכול חוץ מ-2"
    batch["items"] = batch["items"][1:]
    assert SP.reply_for(batch, by_rule) == "לדלג על המנה"
    topics = {"stage": "topics", "items": [
        {"n": 1, "rule_id": "R3", "cells": [{"legal": True}]},
        {"n": 2, "rule_id": "R1", "cells": [{"legal": False}]},
        {"n": 3, "rule_id": "R4", "cells": [{"legal": True}]},
        {"n": 4, "rule_id": "R9", "cells": []}]}
    assert SP.reply_for(topics, by_rule).splitlines() == ["1 נבדק ולאשר", "2 לאשר", "3 לעורך דין", "4 לדלג"]
    assert SP.reply_for({"stage": "questions", "items": [{"n": 1}]}, by_rule) is None


def test_page_decisions_go_through_the_official_queue_past_an_open_question(tmp_path):
    """התור פותח בשאלה פתוחה לפני הנושאים. הקליטה מהעמוד עוברת אותה, מאשרת את מה שאושר בעמוד, ומשאירה את השאר."""
    m, p, rec = _model(tmp_path)
    init = SP.build_init(m, str(p), str(rec), APPROVER)
    free = [x for x in init["positions"] if not x["legal"]]
    assert len(free) >= 2
    ok, change = free[0]["id"], free[1]["id"]
    dec = {"family": "x", "approver": APPROVER, "date": "2026-11-02", "decisions": [
        {"rule_id": ok, "decision": "approved"},
        {"rule_id": change, "decision": "change_requested", "note": "לקצר ל-30 יום"}]}
    d = tmp_path / "decisions.json"
    d.write_text(json.dumps(dec, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-B", str(CLI), "apply", "--decisions", str(d), "--model", str(p),
                        "--records", str(rec), "--local-copy-dir", str(tmp_path / "local")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    model = json.loads(p.read_text(encoding="utf-8"))
    st = S.derive_status(model, S.record_cells_for(model, str(p)))
    approved = set(st["approved_keys"])
    assert any(k.startswith(ok + "|") for k in approved), r.stdout
    assert not any(k.startswith(change + "|") for k in approved)
    assert "לקצר ל-30 יום" in r.stdout, "השינוי המבוקש מוחזר לסוכן"
    assert "שאלות פתוחות" in r.stdout, "מה שהעמוד לא מכריע בו נשאר בתור ומדווח"
    assert not (Path.home() / "Areo-playbooks-local" / "x").exists()


def test_lawyer_later_is_kept_as_its_own_reason(tmp_path):
    """"עורך דין יעבור אחר כך" אינו מאשר דבר, ונשמר עם הסיבה, כדי שסביבת העבודה תציג "מחכה לעורך דין"."""
    m, p, rec = _model(tmp_path)
    init = SP.build_init(m, str(p), str(rec), APPROVER)
    rid = init["positions"][0]["id"]
    dec = {"family": "x", "approver": APPROVER, "date": "2026-11-03",
           "decisions": [{"rule_id": rid, "decision": "legal_review_later"}]}
    d = tmp_path / "decisions.json"
    d.write_text(json.dumps(dec, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, "-B", str(CLI), "apply", "--decisions", str(d), "--model", str(p),
                        "--records", str(rec), "--local-copy-dir", str(tmp_path / "local")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    model = json.loads(p.read_text(encoding="utf-8"))
    cells = S.record_cells_for(model, str(p)) or {}
    mine = {k: v for k, v in cells.items() if k.startswith(rid + "|")}
    assert mine and all(v.get("lawyer_later") and v["status"] == "skipped" for v in mine.values()), mine
    assert not any(k.startswith(rid + "|") for k in S.derive_status(model, cells)["approved_keys"])
