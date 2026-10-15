# -*- coding: utf-8 -*-
"""בדיקות הקבלה של סביבת העבודה, בדפדפן מדומה, כחלק מכל שחרור.

שמונה רתמות ה-JS שבתיקיית `playbook-workspace/scripts` בודקות את הדף כמו
שמשתמש רואה אותו: כל מסך נרנדר, כל כפתור נלחץ בלי שגיאה, הערות נשמרות
ונמחקות, אין מקפים ארוכים ואין קודים פנימיים בטקסט הגלוי. עד עכשיו הן לא
רצו בשגרה, ושתיים מהן מעולם לא רצו בפועל: לא היה דף שיש בו סגמנטים, ולא
דף שיש בו כמה פלייבוקים.

כאן נבנים שלושה דפים מהנתונים, דרך אותם סקריפטים שבונים דף אצל לקוח:
* **פלייבוק אחד** — ההדגמה.
* **סגמנטים** — ההדגמה ועוד סגמנט רגיל וסגמנט של מכרז, שבו אין משא ומתן.
  הבנייה שלו גילתה שהשכבות של סגמנט כזה לא הועברו מהמודל לדף.
* **כמה פלייבוקים** — שני סוגי הסכמים, עם בורר ואשף לכל סוג.

והרתמות רצות על כל אחד מהם. הן צריכות jsdom (`JSDOM_PATH`). בלעדיו הבדיקה
מדולגת, ובשחרור (`AREO_REQUIRE_JSDOM=1`) היא נכשלת, כי בדיקה שלא רצה אינה
בדיקה שעברה.
"""
import copy
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WS = ROOT / "plugin" / "areolegal" / "skills" / "playbook-workspace" / "scripts"
CONTENT = ROOT / "server" / "content" / "playbook-workspace"
BASIS = (ROOT / "plugin" / "areolegal" / "skills" / "contract-playbook-builder"
         / "scripts" / "basis_line.py")
JSDOM = os.environ.get("JSDOM_PATH", "")

pytestmark = pytest.mark.skipif(not (CONTENT / "demo-playbook-model.json").exists(),
                                reason="עץ התוכן (../server) אינו מחולץ כאן")


def _need_jsdom():
    ok = bool(shutil.which("node")) and JSDOM and Path(JSDOM).exists()
    if ok:
        return
    msg = "אין node או jsdom (JSDOM_PATH), ולכן רתמות הדף לא רצו"
    if os.environ.get("AREO_REQUIRE_JSDOM") == "1":
        pytest.fail(msg)
    pytest.skip(msg)


def _py(script, args):
    r = subprocess.run([sys.executable, str(script)] + [str(a) for a in args],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def _demo():
    return json.loads((CONTENT / "demo-playbook-model.json").read_text(encoding="utf-8"))


def _segments(m):
    """סגמנט רגיל וסגמנט של מכרז, על הכלל הראשון, בשמות שבמודל."""
    rid = m["rules"][0]["rule_id"]
    m["segmentation_model"] = {"status": "Detected", "dimensions": ["סוג המזמין"], "segments": [
        {"segment_id": "SEG-REG", "segment_name": "גוף מפוקח",
         "criteria": "המזמין הוא גוף בפיקוח רגולטורי", "status": "Confirmed",
         "variants": [{"rule_id": rid, "negotiation_mode": "negotiated",
                       "traffic_light": {
                           "green": {"position": "תקרה בגובה התמורה השנתית"},
                           "yellow": {"position": "תקרה בגובה פעמיים התמורה השנתית"},
                           "red": {"position": "אחריות בלי תקרה"}},
                       "segment_rationale": {"executive_segment_rationale":
                                             "גוף מפוקח דורש תקרה גבוהה יותר."}}]},
        {"segment_id": "SEG-BID", "segment_name": "מכרז ציבורי",
         "criteria": "ההתקשרות היא במכרז, ואין משא ומתן על הנוסח", "status": "Confirmed",
         "variants": [{"rule_id": rid, "negotiation_mode": "imposed",
                       "imposed_regime": [{"topic": "אחריות", "imposed": "אחריות בלי תקרה",
                                           "effect": "חשיפה בלתי מוגבלת"}],
                       "clarification_positions": {
                           "green": {"pos": "תקרה בגובה התמורה"},
                           "yellow": {"pos": "תקרה בגובה פעמיים התמורה",
                                      "label": "הצעת Areo (לא מבוסס על מסמכי הלקוח)"}},
                       "bid_conditions": [{"recommendation": "ניגשים רק באישור הנהלה ועם ביטוח מתאים",
                                           "combination": "אחריות בלי תקרה יחד עם שיפוי מלא",
                                           "why": "החשיפה אינה מוגבלת, ולכן ההחלטה של ההנהלה."}],
                       "segment_rationale": {"executive_segment_rationale":
                                             "במכרז הנוסח נכפה, והעמדה עולה בשאלות ההבהרה."}}]},
    ]}
    return m


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    out = tmp_path_factory.mktemp("pages")
    tpl, wiz = CONTENT / "dashboard_template.html", CONTENT / "wizard_template.html"
    meta = CONTENT / "demo-playbook-meta.json"

    def build(model, name, extra=()):
        mp = out / (name + "-model.json")
        mp.write_text(json.dumps(model, ensure_ascii=False), encoding="utf-8")
        pp = out / (name + "-payload.json")
        _py(WS / "build_workspace_payload.py", [mp, pp, "--meta", meta])
        _py(WS / "validate_data.py", ["--data", pp])
        _py(WS / "build_dashboard.py", [tpl, pp, out / (name + ".html"),
                                        "--artifact", out / (name + ".art.html")] + list(extra))
        return pp

    build(_demo(), "single")
    seg_payload = build(_segments(_demo()), "seg")

    # שני סוגי הסכמים, כל אחד בקובץ משלו, ודף אחד מהאינדקס
    data = out / "client" / "Areo-נתונים"
    entries = []
    for fid, label, role, keep in (("fam_services_recipient", "הסכם שירותים", "מקבל השירותים", None),
                                   ("fam_nda_mutual", "הסכם סודיות", "הדדי", 3)):
        m = _demo()
        m["family_id"] = m["playbook_id"] = fid
        sc = m.setdefault("scope_summary", {})
        fams = sc.get("contract_families") or [{}]
        fams[0] = dict(fams[0] or {}, contract_family_name=label, company_role=role)
        sc["contract_families"] = fams
        if keep:
            m["rules"] = m["rules"][:keep]
        d = data / "playbooks" / fid
        d.mkdir(parents=True)
        (d / "playbook-model.json").write_text(json.dumps(m, ensure_ascii=False), encoding="utf-8")
        entries.append({"core_path": "playbooks/%s/playbook-core.json" % fid, "family_id": fid})
    (data / "playbooks" / "index.json").write_text(json.dumps({"playbooks": entries}),
                                                     encoding="utf-8")
    mp = out / "multi-payload.json"
    _py(WS / "build_workspace_payload.py", ["--data", data, mp, "--meta", meta])
    _py(WS / "validate_data.py", ["--data", mp])
    _py(WS / "build_dashboard.py", [tpl, mp, out / "multi.html", "--artifact",
                                    out / "multi.art.html", "--wizard", wiz])
    return {"dir": out, "seg_payload": seg_payload}


def test_the_imposed_layers_reach_the_page(pages):
    """הבאג שהבדיקה הזאת גילתה: שלוש השכבות לא הועברו מהמודל לדף."""
    p = json.loads(pages["seg_payload"].read_text(encoding="utf-8"))
    v = next(v for r in p["rules"] for v in (r.get("variants") or []) if v["seg"] == "SEG-BID")
    assert v["mode"] == "imposed"
    assert v["imposed_regime"] and v["clarification_positions"] and v["bid_conditions"]


RUNS = [
    ("single", "qa_dashboard", []),
    ("single", "qa_basis", []),
    ("single", "qa_basis_line", [BASIS]),
    ("single", "qa_artifact", ["@single.art.html"]),
    ("single", "qa_shared_decisions", []),
    ("seg", "qa_dashboard", []),
    ("seg", "qa_imposed", []),
    ("seg", "qa_segments", []),
    ("multi", "qa_dashboard", []),
    ("multi", "qa_shared_decisions", []),
    ("multi", "qa_scope", []),
    ("multi", "qa_artifact", ["@multi.art.html"]),
]


@pytest.mark.parametrize("page,harness,extra", RUNS,
                         ids=["%s-%s" % (p, h) for p, h, _ in RUNS])
def test_the_page_harness_passes(pages, page, harness, extra):
    _need_jsdom()
    args = [str(pages["dir"] / (page + ".html"))]
    args += [str(pages["dir"] / a[1:]) if str(a).startswith("@") else str(a) for a in extra]
    r = subprocess.run(["node", str(WS / (harness + ".js"))] + args,
                       capture_output=True, text=True, timeout=180,
                       env=dict(os.environ, JSDOM_PATH=JSDOM))
    tail = "\n".join((r.stdout + r.stderr).strip().splitlines()[-12:])
    assert r.returncode == 0, tail
    if harness == "qa_segments":
        assert "אין סגמנטים" not in r.stdout, "הרתמה לא מצאה סגמנטים, ולכן לא בדקה דבר"


RISK = ROOT / "plugin" / "areolegal" / "skills" / "contract-risk-assessor" / "scripts"
RISK_TPL = ROOT / "server" / "content" / "contract-risk-assessor" / "risk-report-template.html"


def test_the_risk_report_loads_and_renders_every_screen(tmp_path):
    """דוח הסיכונים: שורת פרוזה אחת בתוך הסקריפט כבר רוקנה את כל הדף פעם."""
    _need_jsdom()
    out = tmp_path / "risk.html"
    _py(RISK / "build_risk_report.py", ["--data", RISK / "risk_smoke_fixture.json",
                                        "--template", RISK_TPL, "--out", out])
    r = subprocess.run(["node", str(RISK / "qa_risk_smoke.js"), str(out)],
                       capture_output=True, text=True, timeout=180,
                       env=dict(os.environ, JSDOM_PATH=JSDOM))
    assert r.returncode == 0, "\n".join((r.stdout + r.stderr).strip().splitlines()[-12:])
