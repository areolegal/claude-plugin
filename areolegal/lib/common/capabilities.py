# -*- coding: utf-8 -*-
"""common/capabilities.py: יכולות הריצה שעמוד Areo מצהיר כשהוא מתפרסם כ-Artifact, ובדיקה שהן מוצהרות.

עמוד שקורא ל-claude.use("db") בלי הצהרה מקבל null, וההערות המשותפות נשארות בדפדפן של כל קורא בלי שאיש יודע.
לכן ההצהרה כתובה כאן פעם אחת לכל סוג עמוד, סקריפט ההפקה מדפיס אותה עם תוכן העמוד המשותף, והבדיקה נכשלת כשתבנית
קוראת ליכולת שאינה בהצהרה.

שימוש:
  python capabilities.py --kind workspace --templates dashboard_template.html wizard_template.html
  קוד יציאה 0 כשכל יכולת שהתבניות קוראות לה מוצהרת, 3 כשלא. מדפיס את ההצהרה ב-JSON.
"""
import argparse
import io
import json
import re
import sys

if __name__ == '__main__':
    sys.dont_write_bytecode = True

# ההצהרה לכל סוג עמוד. מסד ההערות: כל קורא רואה, רק Contributor ומעלה כותב הערה, ואישור (approvals) נכתב
# רק בידי עורכים (admin), כך שרק מי שיש לו הרשאת עריכה מאשר. שמות מוצגים לפי מזהה (user, scope profile).
CAPABILITIES = {
    "workspace": {
        "db": {"rules": [{"path": "comments", "read": "view", "write": "interact"},
                         {"path": "approvals", "read": "view", "write": "admin"}]},
        "user": {"scopes": ["profile"]},
        "downloads": True,
    },
    # דוח הסיכונים ומרכז ההיערכות אינם משתמשים ביכולות: עמוד חסוי, בלי מסד ובלי נכסים
    "risk": {},
    "prep_center": {},
}

USE_RX = re.compile(r"""claude\.use\(\s*['"]([a-z]+)['"]\s*\)""")


def used_capabilities(paths):
    names = set()
    for p in paths:
        with io.open(p, encoding="utf-8", errors="replace") as fh:
            names.update(USE_RX.findall(fh.read()))
    names.discard("permissions")   # מובנית, לעולם אינה מוצהרת
    return names


def missing(kind, paths):
    """יכולות שהתבניות קוראות להן ואינן בהצהרה של סוג העמוד."""
    declared = set(CAPABILITIES.get(kind, {}))
    return sorted(used_capabilities(paths) - declared)


def main(argv=None):
    ap = argparse.ArgumentParser(description="ההצהרה על יכולות הריצה של עמוד Areo, ובדיקה שכל יכולת שהתבנית "
                                             "קוראת לה מוצהרת")
    ap.add_argument("--kind", required=True, choices=sorted(CAPABILITIES))
    ap.add_argument("--templates", nargs="+", required=True, help="קובצי התבנית שהעמוד המשותף נבנה מהם")
    a = ap.parse_args(argv)
    miss = missing(a.kind, a.templates)
    print(json.dumps({"capabilities": CAPABILITIES[a.kind], "missing": miss}, ensure_ascii=False))
    if miss:
        print("חסרה הצהרה על: %s. הוסיפו אותן ל-CAPABILITIES['%s'] לפני הפרסום" % (", ".join(miss), a.kind))
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
