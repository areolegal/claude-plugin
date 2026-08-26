# -*- coding: utf-8 -*-
"""מאמת את strategy-data.json מול הסכמה שהתבנית יודעת להציג, לפני ההזרקה.

הרציונל: התבנית אינה נקראת להקשר, ולכן ערך שאינו מוכר לה אינו מתריע.
הסקריפט רץ, הקובץ נוצר, ומסך שלם מוצג ריק.

שימוש:
  python3 validate_data.py --data strategy-data.json [--strict]
"""
import argparse
import io
import json
import re
import sys

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ENUMS = {
    "risk.severity": {"critical", "high", "medium", "low"},
    "node.side": {"us", "them"},
    "node.level": {"hard", "soft", "open", "bridge"},
    "dialogue.who": {"us", "them"},
    "docAccess.mode": {"local", "connector", "base", "none"},
}

TOP_LEVEL = ["meta", "counters", "clauses", "risks", "plan", "companion", "footnotes"]
LINES = ("red", "yellow", "bridge")


class Report(object):
    def __init__(self):
        self.errors, self.warns = [], []

    def err(self, w, m):
        self.errors.append((w, m))

    def warn(self, w, m):
        self.warns.append((w, m))


def check_enum(r, where, field, value, key, required=True):
    if value in (None, ""):
        if required:
            r.err(where, "השדה %s ריק, והוא שדה חובה" % field)
        return
    if value not in ENUMS[key]:
        r.err(where, "הערך %r בשדה %s אינו מוכר לתבנית. הערכים המותרים: %s"
              % (value, field, ", ".join(sorted(ENUMS[key]))))


def check_date(r, where, field, value, required=False):
    if value in (None, ""):
        if required:
            r.err(where, "השדה %s ריק, ונדרש תאריך" % field)
        return
    if not ISO.match(str(value)):
        r.err(where, "השדה %s בערך %r אינו בפורמט ISO של YYYY-MM-DD" % (field, value))


def validate(data):
    r = Report()
    for k in TOP_LEVEL:
        if k not in data:
            r.err("שורש הקובץ", "המפתח %r חסר. התבנית קוראת אותו, והיעדרו מרוקן מסך" % k)

    meta = data.get("meta") or {}
    for f in ("company", "counterparty", "transaction_id"):
        if not meta.get(f):
            r.err("meta", "meta.%s חסר. הוא נדרש לכותרת ולשמירת הסימונים בדפדפן" % f)
    check_date(r, "meta", "generated_at", meta.get("generated_at"), required=True)
    check_date(r, "meta", "last_updated", meta.get("last_updated"))
    if not isinstance(meta.get("round_number"), int):
        r.warn("meta", "round_number אינו מספר שלם. מספר הסבב לא יוצג נכון")
    st = meta.get("status") or {}
    if not st.get("text"):
        r.err("meta.status", "text חסר. מסך תמונת המצב יציג שטרם נמסר סטטוס")
    if st.get("text") and not st.get("source"):
        r.err("meta.status", "נמסר סטטוס בלי source. כל קביעה נושאת את מקורה, "
                             "למשל דיווח משתמש או מייל")
    check_date(r, "meta.status", "date", st.get("date"))
    health = meta.get("health") or {}
    if not health.get("label"):
        r.warn("meta.health", "label ריק. מדד בריאות העסקה יוצג כלא נקבע")
    acc = meta.get("docAccess") or {}
    if acc:
        check_enum(r, "meta.docAccess", "mode", acc.get("mode"), "docAccess.mode", required=False)

    fn_nums = set()
    for i, f in enumerate(data.get("footnotes") or []):
        where = "footnotes[%d]" % i
        n = f.get("n")
        if not isinstance(n, int):
            r.err(where, "n חייב להיות מספר שלם, ולא %r" % n)
        if n in fn_nums:
            r.err(where, "מספר הערת שוליים %r חוזר" % n)
        fn_nums.add(n)
        if not f.get("quote"):
            r.err(where, "quote חסר. הערת השוליים תיפתח ריקה")
        check_date(r, where, "date", f.get("date"))

    def check_refs(where, refs):
        for n in refs or []:
            if n not in fn_nums:
                r.err(where, "הפניה להערת שוליים %r שאינה קיימת. "
                             "הסימון בממשק יוביל לחלון ריק" % n)

    counters = data.get("counters") or {}
    for k in ("aligned", "disputed", "redline"):
        if not isinstance(counters.get(k), int):
            r.err("counters", "המונה %r חסר או אינו מספר שלם. הכרטיס יוצג ריק" % k)

    clause_ids = set()
    for i, c in enumerate(data.get("clauses") or []):
        where = "clauses[%d] (%s)" % (i, c.get("title", "ללא כותרת"))
        cid = c.get("id")
        if not cid:
            r.err(where, "id חסר")
        if cid in clause_ids:
            r.err(where, "מזהה הסעיף %r חוזר" % cid)
        clause_ids.add(cid)
        if not c.get("title"):
            r.err(where, "title חסר. כרטיס הסעיף יוצג בלי שם")
        pb = c.get("playbook") or {}
        if not pb.get("position"):
            r.err(where, "playbook.position חסר. לא יהיה ברור מה עמדת המדיניות")
        lines = c.get("lines") or {}
        for L in LINES:
            band = lines.get(L)
            if not isinstance(band, dict):
                r.err(where, "lines.%s חסר. שלושת הקווים חובה בכל סעיף במחלוקת" % L)
                continue
            key = "wording" if L == "bridge" else "what"
            if not band.get(key):
                r.err("%s.lines.%s" % (where, L), "%s ריק. תא הקו יוצג ריק" % key)
        check_refs(where, c.get("refs"))
        for j, n in enumerate(c.get("tree") or []):
            nw = "%s.tree[%d]" % (where, j)
            check_enum(r, nw, "side", n.get("side"), "node.side")
            check_enum(r, nw, "level", n.get("level"), "node.level", required=False)
            if not n.get("text"):
                r.err(nw, "text חסר")
            check_refs(nw, n.get("refs"))
        dlg = c.get("dialogue") or []
        for j, d in enumerate(dlg):
            check_enum(r, "%s.dialogue[%d]" % (where, j), "who", d.get("who"), "dialogue.who")
        if dlg and len(dlg) < 8:
            r.warn(where, "התסריט מכיל %d חילופי דברים. המפרט דורש 8 עד 12, "
                          "אחרת הוא קורא כתקציר ולא כאימון" % len(dlg))
        b = c.get("bargain") or {}
        for j, m in enumerate(b.get("midpoints") or []):
            if not m.get("point"):
                r.err("%s.bargain.midpoints[%d]" % (where, j), "point חסר")
            if not m.get("criterion"):
                r.err("%s.bargain.midpoints[%d]" % (where, j),
                      "criterion חסר. נקודת אמצע בלי קריטריון אינה ניתנת להגנה בשיחה")

    for i, k in enumerate(data.get("risks") or []):
        where = "risks[%d] (%s)" % (i, k.get("title", "ללא כותרת"))
        check_enum(r, where, "severity", k.get("severity"), "risk.severity")
        if not k.get("title"):
            r.err(where, "title חסר")
        if not k.get("mitigation"):
            r.err(where, "mitigation ריק. סיכון בלי המלצת צמצום אינו מוסר החלטה")
        cid = k.get("clause_id")
        if cid and cid not in clause_ids:
            r.err(where, "clause_id %r אינו קיים ברשימת הסעיפים" % cid)
        check_refs(where, k.get("refs"))

    plan = data.get("plan") or {}
    nm = plan.get("next_move") or {}
    if not nm.get("title"):
        r.err("plan.next_move", "title חסר. מסך ההכנה יציג שלא הוגדר מהלך הבא")
    if nm.get("title") and not nm.get("why"):
        r.err("plan.next_move", "why חסר. מהלך בלי נימוק אינו ניתן להערכה")
    order = plan.get("order") or []
    if not order:
        r.err("plan.order", "לא הוגדר סדר שיחה")
    for i, s in enumerate(order):
        if not s.get("step"):
            r.err("plan.order[%d]" % i, "step חסר")
        if not s.get("why"):
            r.err("plan.order[%d]" % i, "why חסר. כל שלב בסדר השיחה נושא נימוק של שורה")
    for side in ("give", "ask"):
        for i, x in enumerate(plan.get(side) or []):
            if not x.get("what"):
                r.err("plan.%s[%d]" % (side, i), "what חסר")
            if not x.get("why"):
                r.err("plan.%s[%d]" % (side, i), "why חסר")
    if plan.get("give") and not plan.get("ask"):
        r.err("plan", "הוגדר מה נותנים בלי מה מבקשים בתמורה. "
                      "ויתור בלי תמורה אינו חבילה אלא ויתור")

    cmp_ = data.get("companion") or {}
    if not (cmp_.get("pocket") or []):
        r.err("companion.pocket", "כרטיס הכיס ריק. זהו התוצר שנלקח לשיחה עצמה")
    if not (cmp_.get("donot") or []):
        r.warn("companion.donot", "רשימת מה לא אומרים ריקה")
    if not cmp_.get("pause_line"):
        r.warn("companion", "לא הוגדר משפט הפסקה")
    for k in ("pocket", "redlines", "donot", "briefing"):
        v = cmp_.get(k)
        if v is not None and not isinstance(v, list):
            r.err("companion.%s" % k, "חייב להיות מערך מחרוזות, ולא %s" % type(v).__name__)

    for i, e in enumerate(data.get("timeline") or []):
        where = "timeline[%d]" % i
        check_date(r, where, "date", e.get("date"), required=True)
        if not e.get("event"):
            r.err(where, "event חסר")
        if not e.get("source"):
            r.err(where, "source חסר. אירוע בציר הזמן נושא תמיד את מקורו")

    if not (data.get("clauses") or []):
        r.warn("clauses", "אין סעיפים במחלוקת. הלשונית תוצג עם הודעת ריק מכוונת")

    return r


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--strict", action="store_true")
    a = p.parse_args()
    try:
        data = json.load(io.open(a.data, encoding="utf-8"))
    except ValueError as e:
        print("שגיאה: הקובץ אינו JSON תקין. %s" % e)
        sys.exit(1)
    r = validate(data)
    if r.errors:
        print("נמצאו %d שגיאות חוסמות. אין להזריק לתבנית לפני תיקונן:" % len(r.errors))
        for w, m in r.errors:
            print("  [%s] %s" % (w, m))
    if r.warns:
        print("%d אזהרות:" % len(r.warns))
        for w, m in r.warns:
            print("  [%s] %s" % (w, m))
    if not r.errors and not r.warns:
        print("בדיקת הסכמה עברה במלואה. הנתונים תואמים את מה שהתבנית יודעת להציג.")
    elif not r.errors:
        print("אין שגיאות חוסמות. ניתן להזריק.")
    sys.exit(1 if r.errors or (a.strict and r.warns) else 0)


if __name__ == "__main__":
    main()
