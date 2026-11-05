# -*- coding: utf-8 -*-
"""common/record_action.py: דיווח על פעולה שהושלמה, כמונה בלבד (areo-hard-rules.md, 3.14).

המונה הוא כל מה ש-Areo רואה על העבודה: מזהה הסקיל, סוג הפעולה, מספר ותאריך. אין בו תוכן, שם קובץ, נתיב, שם לקוח
או מזהה של תוצר. הסקריפט אינו מתקשר עם השרת: הוא בודק שהפעולה נספרת, מונע ספירה כפולה של אותו תוצר, ומדפיס את
ארבעת השדות שהסוכן מוסר לכלי `record_action` של שירות areolegal (כשהשירות מציע כלי כזה; אחרת אין שליחה ואין
המצאת כלי).

שימוש:
  python3 -B record_action.py --skill setup --action profile_built --output-id "<מזהה מקומי של התוצר>"
                                --ledger "<תיקיית Areo-נתונים>"
  --output-id: מחרוזת מקומית שמזהה את התוצר (למשל נתיב הקובץ שהופק). היא נשמרת בפנקס המקומי כגיבוב בלבד,
               בתיקיית הלקוח, ולעולם אינה נשלחת.
  --dry-run:   בודק ומדפיס, בלי לרשום בפנקס.
פלט (stdout): שורת JSON אחת, {"skill":..., "action":..., "count": 1, "date": "YYYY-MM-DD"}, או ריק כשהתוצר כבר נספר.
קוד יציאה: 0 תקין (כולל "כבר נספר"), 2 קלט שאינו נספר או לא תקין.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys

if __name__ == "__main__":
    sys.dont_write_bytecode = True

# הפעולות שנספרות, לפי כלל 1.7: סקיל -> סוגי פעולה. שאלה, תצוגה מקדימה, ריצה שנעצרה לפני התוצר, עדכון שדה בפרופיל
# ושאילתה במרשם אינם פעולה, ולכן אינם ברשימה.
ACTIONS = {
    "setup": ("profile_built", "entity_added"),
    "playbook": ("playbook_built", "playbook_updated"),
    "negotiator": ("round_produced", "signing_copy_produced"),
    "drafter": ("draft_produced",),
    "risk": ("risk_report", "background_check_report"),
    "strategist": ("prep_center",),
    "translator": ("translation_produced",),
    "register": ("agreement_registered",),
    "clm": ("workspace_built", "workspace_updated"),
}
LEDGER_NAME = ".areo-actions.json"
PAYLOAD_KEYS = ("skill", "action", "count", "date")


def payload(skill, action, today=None):
    """המונה עצמו: ארבעה שדות בלבד. ValueError על פעולה שאינה נספרת."""
    if skill not in ACTIONS:
        raise ValueError("unknown skill: %s" % skill)
    if action not in ACTIONS[skill]:
        raise ValueError("not a counted action for %s: %s (counted: %s)" % (skill, action, ", ".join(ACTIONS[skill])))
    out = {"skill": skill, "action": action, "count": 1, "date": (today or datetime.date.today()).isoformat()}
    assert tuple(out) == PAYLOAD_KEYS
    return out


def _digest(skill, action, output_id):
    return hashlib.sha256(("%s|%s|%s" % (skill, action, output_id)).encode("utf-8")).hexdigest()


def record(skill, action, output_id, ledger_dir=None, today=None, dry_run=False):
    """מחזיר את המונה לשליחה, או None כשאותו תוצר כבר נספר. הפנקס (בתיקיית הלקוח בלבד) שומר גיבובים."""
    p = payload(skill, action, today)
    if not output_id:
        raise ValueError("output id is required (one action per completed output)")
    d = _digest(skill, action, output_id)
    path = os.path.join(ledger_dir, LEDGER_NAME) if ledger_dir else None
    seen = []
    if path and os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as fh:
                seen = json.load(fh).get("counted", [])
        except (OSError, ValueError):
            seen = []
    if d in seen:
        return None
    if path and not dry_run:
        os.makedirs(ledger_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"counted": seen + [d]}, fh)
    return p


def main(argv=None):
    ap = argparse.ArgumentParser(description="מונה פעולה שהושלמה (בלי תוכן)")
    ap.add_argument("--skill", required=True, choices=sorted(ACTIONS))
    ap.add_argument("--action", required=True)
    ap.add_argument("--output-id", required=True, help="מזהה מקומי של התוצר; נשמר כגיבוב בלבד ואינו נשלח")
    ap.add_argument("--ledger", help="תיקיית Areo-נתונים של הלקוח (לפנקס נגד ספירה כפולה)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    try:
        p = record(a.skill, a.action, a.output_id, a.ledger, dry_run=a.dry_run)
    except ValueError as exc:
        print("לא נספר: %s" % exc, file=sys.stderr)
        return 2
    if p:
        print(json.dumps(p, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
