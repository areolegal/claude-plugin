# -*- coding: utf-8 -*-
"""מאמת את payload הפלייבוק מול הסכמה שהתבנית יודעת להציג, לפני ההזרקה.

הרציונל: התבנית אינה נקראת להקשר, ולכן ערך שאינו מוכר לה אינו מתריע.
הסקריפט רץ, הקובץ נוצר, ולשונית שלמה מוצגת ריקה או נופלת לברירת מחדל שגויה.

שימוש:
  python3 validate_data.py --data payload.json [--strict]

קוד יציאה 0: תקין. קוד יציאה 1: נמצאו שגיאות חוסמות.
"""
import argparse
import io
import json
import re
import sys

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ENUMS = {
    "rule.conf": {"High", "Medium", "Low"},
    "rule.reg": {"Researched", "NotResearched", "NotApplicable"},
    "presence.requirement": {"Required", "Recommended", "Optional", "Prohibited"},
    "presence.missing_clause_color": {"Green", "Yellow", "Red"},
    "ev.weight": {"High", "Medium", "Low"},
    "cite.side": {"pro", "con", "neutral"},
    "source.kind": {"internal", "external"},
    "precedent.direction": {"stricter", "easier", "neutral"},
    "finding.severity": {"high", "medium", "low"},
    "meta.status": {"Draft", "Approved", "Superseded"},
    "rat.rationale_status": {"Draft", "Confirmed"},
    "reg.status": {"Performed", "NotPerformed", "Partial"},
}

LIGHTS = ("green", "yellow", "red")
TOP_LEVEL = ["meta", "scope", "sources", "cites", "rules", "segments",
             "precedents", "templateFindings", "queue"]


class Report(object):
    def __init__(self):
        self.errors = []
        self.warns = []

    def err(self, where, msg):
        self.errors.append((where, msg))

    def warn(self, where, msg):
        self.warns.append((where, msg))


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
            r.err("שורש הקובץ", "המפתח %r חסר. התבנית קוראת אותו, והיעדרו מרוקן לשונית" % k)

    meta = data.get("meta") or {}
    for f in ("id", "slug", "ls_key", "company", "title", "version"):
        if not meta.get(f):
            r.err("meta", "meta.%s חסר. הוא נדרש לזיהוי הפלייבוק ולשמירת סימונים בדפדפן" % f)
    check_enum(r, "meta", "status", meta.get("status"), "meta.status")
    check_date(r, "meta", "created", meta.get("created"))
    check_date(r, "meta", "updated", meta.get("updated"))
    if meta.get("ls_key") and not re.match(r"^[A-Za-z0-9_]+$", str(meta["ls_key"])):
        r.err("meta", "ls_key מכיל תווים שאינם אותיות לטיניות, ספרות או קו תחתון. "
                      "מפתח כזה שובר את שמירת הסימונים בדפדפן")

    scope = data.get("scope") or {}
    fams = scope.get("contract_families") or []
    if not fams:
        r.err("scope", "לא הוגדרה אף משפחת הסכמים. הכותרת ותיאור התחולה יוצגו ריקים")
    for i, f in enumerate(fams):
        if not f.get("contract_family_name"):
            r.err("scope.contract_families[%d]" % i, "contract_family_name חסר")
        if not f.get("company_role"):
            r.warn("scope.contract_families[%d]" % i,
                   "company_role ריק. עמדת החברה במשפחה אינה מוצגת")

    reg = data.get("reg")
    if isinstance(reg, dict):
        check_enum(r, "reg", "status", reg.get("status"), "reg.status", required=False)

    sources = data.get("sources") or {}
    if isinstance(sources, list):
        r.err("sources", "sources הוא מערך, אך התבנית מצפה לאובייקט שממפה מזהה מקור לפרטיו")
        sources = {}
    for sid, s in sources.items():
        where = "sources[%s]" % sid
        check_enum(r, where, "kind", (s or {}).get("kind"), "source.kind")
        if not (s or {}).get("label"):
            r.err(where, "label חסר. המקור יוצג כקוד פנימי במקום בשם ידידותי")

    cite_ids = set()
    rule_ids = set(x.get("id") for x in data.get("rules") or [])
    for i, c in enumerate(data.get("cites") or []):
        where = "cites[%d]" % i
        cid = c.get("id")
        if not cid:
            r.err(where, "id חסר")
        if cid in cite_ids:
            r.err(where, "מזהה הציטוט %r חוזר" % cid)
        cite_ids.add(cid)
        if not c.get("text"):
            r.err(where, "text חסר. הערת השוליים תיפתח ריקה")
        if c.get("src") and c["src"] not in sources:
            r.err(where, "src %r אינו קיים ב-sources. הציטוט לא ישויך לאף מקור" % c["src"])
        check_enum(r, where, "side", c.get("side"), "cite.side", required=False)
        for rid in c.get("rules") or []:
            if rid not in rule_ids:
                r.err(where, "מפנה לכלל %r שאינו קיים" % rid)

    seg_ids = set(s.get("segment_id") for s in data.get("segments") or [])
    for i, s in enumerate(data.get("segments") or []):
        where = "segments[%d]" % i
        if not s.get("segment_id"):
            r.err(where, "segment_id חסר")
        if not s.get("label"):
            r.err(where, "label חסר. הסגמנט יוצג כקוד פנימי")
        if not s.get("criteria"):
            r.warn(where, "criteria ריק. לא יהיה ברור מתי הסגמנט חל")

    seen_rule = set()
    for i, rule in enumerate(data.get("rules") or []):
        rid = rule.get("id") or "?"
        where = "rules[%d] (%s)" % (i, rid)
        if rid in seen_rule:
            r.err(where, "מזהה הכלל %r חוזר" % rid)
        seen_rule.add(rid)
        for f in ("id", "topic", "issue"):
            if not rule.get(f):
                r.err(where, "השדה %r חסר, והוא שדה חובה בכרטיס הכלל" % f)
        pres = rule.get("presence") or {}
        check_enum(r, where + ".presence", "requirement", pres.get("requirement"),
                   "presence.requirement")
        check_enum(r, where + ".presence", "missing_clause_color",
                   pres.get("missing_clause_color"), "presence.missing_clause_color")
        tl = rule.get("tl") or {}
        for color in LIGHTS:
            band = tl.get(color)
            if not isinstance(band, dict):
                r.err(where, "הרמזור חסר את המצב %r. שלושת המצבים חובה בכל כלל" % color)
                continue
            if not band.get("pos"):
                r.err("%s.tl.%s" % (where, color), "pos ריק. תא הרמזור יוצג ריק")
            crit = band.get("crit")
            if crit is None:
                r.err("%s.tl.%s" % (where, color), "crit חסר. התבנית מצפה למערך קריטריונים")
            elif not isinstance(crit, list):
                r.err("%s.tl.%s" % (where, color), "crit חייב להיות מערך, ולא %s"
                      % type(crit).__name__)
        check_enum(r, where, "conf", rule.get("conf"), "rule.conf")
        rat = rule.get("rat") or {}
        rs = rat.get("rationale_status")
        if rs is None:
            r.warn(where, "אין rationale_status. הנושא יוצג כטיוטה בסביבת העבודה")
        else:
            check_enum(r, where + ".rat", "rationale_status", rs,
                       "rat.rationale_status", required=False)
        check_enum(r, where, "reg", rule.get("reg"), "rule.reg", required=False)
        for j, e in enumerate(rule.get("ev") or []):
            ew = "%s.ev[%d]" % (where, j)
            if e.get("source_id") and e["source_id"] not in sources:
                r.err(ew, "source_id %r אינו קיים ב-sources" % e["source_id"])
            check_enum(r, ew, "weight", e.get("weight"), "ev.weight", required=False)
        for rel in rule.get("rel") or []:
            if rel not in rule_ids:
                r.err(where, "rel מפנה לכלל %r שאינו קיים" % rel)
        for j, im in enumerate(rule.get("impacts") or []):
            if im.get("related_rule_id") and im["related_rule_id"] not in rule_ids:
                r.err("%s.impacts[%d]" % (where, j),
                      "related_rule_id %r אינו קיים" % im["related_rule_id"])
        for j, v in enumerate(rule.get("variants") or []):
            vw = "%s.variants[%d]" % (where, j)
            if v.get("seg") and v["seg"] not in seg_ids:
                r.err(vw, "seg %r אינו קיים ברשימת הסגמנטים" % v["seg"])
            vtl = v.get("tl") or {}
            for color in vtl:
                if color not in LIGHTS:
                    r.err(vw, "מצב רמזור %r אינו מוכר. המצבים הם green, yellow, red" % color)

    for i, p in enumerate(data.get("precedents") or []):
        where = "precedents[%d]" % i
        check_enum(r, where, "direction", p.get("direction"), "precedent.direction")
        for rid in p.get("rules") or []:
            if rid not in rule_ids:
                r.err(where, "מפנה לכלל %r שאינו קיים" % rid)
        for cid in p.get("cites") or []:
            if cid not in cite_ids:
                r.err(where, "מפנה לציטוט %r שאינו קיים" % cid)

    for i, f in enumerate(data.get("templateFindings") or []):
        where = "templateFindings[%d]" % i
        check_enum(r, where, "severity", f.get("severity"), "finding.severity")
        if not f.get("title"):
            r.err(where, "title חסר")
        for cid in f.get("cites") or []:
            if cid not in cite_ids:
                r.err(where, "מפנה לציטוט %r שאינו קיים" % cid)

    for i, q in enumerate(data.get("queue") or []):
        where = "queue[%d]" % i
        if not q.get("question"):
            r.err(where, "question חסר. פריט בלי שאלה אינו ניתן להכרעה")
        if q.get("rule_id") and q["rule_id"] not in rule_ids:
            r.err(where, "rule_id %r אינו קיים" % q["rule_id"])

    for i, c in enumerate(data.get("cross") or []):
        where = "cross[%d]" % i
        for rid in c.get("rules") or []:
            if rid not in rule_ids:
                r.err(where, "צירוף מפנה לכלל %r שאינו קיים" % rid)

    friendly = data.get("friendly") or {}
    for sid in friendly:
        if sid not in sources:
            r.warn("friendly", "השם הידידותי מוגדר למקור %r שאינו קיים ב-sources" % sid)
    for sid in sources:
        if sid not in friendly and sid not in (data.get("shortx") or {}):
            r.warn("sources", "למקור %r אין שם ידידותי, והוא יוצג כקוד פנימי" % sid)

    if not (data.get("rules") or []):
        r.err("rules", "אין אף כלל מדיניות. ה-Workspace יוצג ריק")

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
        for where, msg in r.errors:
            print("  [%s] %s" % (where, msg))
    if r.warns:
        print("%d אזהרות:" % len(r.warns))
        for where, msg in r.warns:
            print("  [%s] %s" % (where, msg))
    if not r.errors and not r.warns:
        print("בדיקת הסכמה עברה במלואה. הנתונים תואמים את מה שהתבנית יודעת להציג.")
    elif not r.errors:
        print("אין שגיאות חוסמות. ניתן להזריק.")
    sys.exit(1 if r.errors or (a.strict and r.warns) else 0)


if __name__ == "__main__":
    main()
