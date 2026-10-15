#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""שער המדיניות: האם מותר לומר על עמדה בפלייבוק שהיא מדיניות החברה.

הנושא ונותן קורא לשער **לכל הכרעה שנשענת על כלל בפלייבוק**, ורושם את התשובה
ב-`policy_gate` של ההכרעה (הערות הפלייבוק 5.5, שינויים 48 ו-65.15; הערות הנושא
ונותן 4.9, "שער המדיניות לכל הכרעה"). השער הוא קוד הייחוס של ענבל
(`areolegal/lib/playbook/status.py`, `policy_claim`), ולא שיקול דעת:

* **`claim: true` רק כשהתא נספר כמאושר** באותה גזירה של מעמד הפלייבוק,
  מרשומת האישור האחרונה שבמודל. פלייבוק במעמד Draft, תא שלא נחתם, תא עם שאלה
  מכרעת פתוחה, ורשומה ישנה בלי ראיה: `claim: false`. התאים נקראים מרשומת
  האישור (`--records`, או הרשומה שהמודל מפנה אליה ב-`approval_records`).
* **הנוסח חייב להיות הנוסח שאושר.** כשנמסר `--wording`, הנוסח שהנושא ונותן
  עומד להחיל מושווה, אחרי נרמול רווחים וסימני כיווניות, לנוסח שנחתם בתא.
  נוסח אחר: `claim: false`, `reason: wording_differs_from_approved`, וזו "נדרשת
  הכרעתך" למשתמש.
* **`claim: false` אינו מונע להחיל את העמדה.** הוא אומר רק שבבועה החיצונית אין
  "מדיניות" ואין "policy", וההכרעה נרשמת PolicyBenchmark.

    python3 scripts/policy_gate.py --model "<playbooks/<family>/playbook-model.json>" \\
        --rule R-07 --track green [--segment SEG-1] [--wording "<הנוסח שיוחל>"]

הפלט הוא JSON אחד, שנכנס כמו שהוא ל-`policy_gate` של ההכרעה בקובץ ההכרעות:
`{claim, status, reason, key, status_label, track, checked_at}`.

קוד יציאה: **0** השער ענה (גם כש-claim הוא false), **2** קלט חסר או כלל שאינו
בפלייבוק.
"""
import argparse
import datetime as _dt
import io
import json
import os
import sys

import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from playbook import ingest_approval as IA  # noqa: E402
from playbook import status as S  # noqa: E402
from playbook.approval_sheet import norm_text  # noqa: E402

TRACKS = ("green", "yellow", "red")


def load_record(a, model):
    """רשומת האישור שהתאים בה: מתיקיית הרשומות, או מהנתיב שהמודל רושם ב-approval_records."""
    if a.records:
        return IA.current_record(a.records)[1]
    entry = S._latest_record(model)
    if not entry or not entry.get("record"):
        return None
    path = entry["record"]
    if not os.path.isabs(path):
        path = os.path.join(os.path.dirname(os.path.abspath(a.model)), path)
    if not os.path.exists(path):
        return None
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model", required=True, help="playbook-model.json של הפלייבוק שנבחר")
    ap.add_argument("--rule", required=True, help="מזהה הכלל, כפי שבפלייבוק")
    ap.add_argument("--track", required=True, choices=TRACKS)
    ap.add_argument("--segment", help="מזהה הסגמנט, כשנבחר סגמנט")
    ap.add_argument("--wording", help="הנוסח שהנושא ונותן עומד להחיל")
    ap.add_argument("--records", help="תיקיית רשומות האישור; בלעדיה: הרשומה האחרונה שהמודל מפנה אליה")
    a = ap.parse_args(argv)

    if not os.path.exists(a.model):
        print("המודל אינו קיים: %s" % a.model)
        return 2
    with io.open(a.model, encoding="utf-8") as fh:
        model = json.load(fh)
    if not any(r.get("rule_id") == a.rule for r in model.get("rules") or ()):
        print("הכלל %s אינו בפלייבוק הזה" % a.rule)
        return 2

    record = load_record(a, model)
    cells = IA.record_cells(record) if record else {}
    wording_fp = None
    if a.wording is not None:
        key = S.cell_key(a.rule, a.track, a.segment)
        cell = cells.get(key) or cells.get(S.cell_key(a.rule, a.track)) or {}
        approved = ((cell.get("approved_text") or {}).get("wording"))
        if approved is not None:
            # הנוסח שאושר: אותה טביעת אצבע כמו בתא; נוסח אחר: טביעה שאינה שלו
            same = norm_text(a.wording) == norm_text(approved)
            wording_fp = cell.get("approved_fp") if same else "differs:" + norm_text(a.wording)[:40]
    res = S.policy_claim(model, cells, a.rule, a.track, a.segment, wording_fp=wording_fp)
    out = {"claim": bool(res["policy_claim"]), "status": res["playbook_status"], "reason": res["reason"],
           "key": res["key"], "status_label": res["status_label"], "track": a.track,
           "checked_at": _dt.datetime.now().astimezone().isoformat(timespec="seconds")}
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
