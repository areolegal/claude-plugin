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
    # הערכים שרכיב הפלייבוק כותב בפועל, ולא רק אלה שתוכננו מראש
    "rule.reg": {"Researched", "NotResearched", "NotApplicable",
                 "ApplicableSourcesFound", "NoApplicableSources"},
    "presence.requirement": {"Required", "Recommended", "Optional", "Prohibited"},
    "presence.missing_clause_color": {"Green", "Yellow", "Red"},
    "ev.weight": {"High", "Medium", "Low"},
    "cite.side": {"pro", "con", "neutral"},
    "cite.track": {"green", "yellow", "red"},
    "source.kind": {"internal", "external"},
    "source.paper": {"ours", "theirs"},
    "rule.kind": {"משפטי", "מסחרי"},
    "precedent.direction": {"stricter", "easier", "neutral"},
    "finding.severity": {"high", "medium", "low"},
    "meta.status": {"Draft", "Approved", "Superseded"},
    "rat.rationale_status": {"Draft", "Confirmed"},
    "reg.status": {"Performed", "Completed", "Partial", "NotPerformed", "Declined"},
    # המסלול שבו הפלייבוק נבנה, לפס הבסיס
    "build_path.path": {"own", "own_plus_market", "market_built"},
    # הרשימה הסגורה של הקודים הטכניים, מ-`clause-catalog.md`
    "technical_code": {"signature_block", "party_identification", "notice_addresses",
                       "counterparts_esignature", "headings", "interpretation_grammar",
                       "recitals_descriptive", "neutral_definition", "bank_details",
                       "delivery_points_list", "admin_form_fields",
                       "statutory_admin_restatement"},
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


COMMERCIAL_ROW = ["src", "field", "found", "norm", "he", "ref", "quote"]


def check_commercial(r, data, sources):
    """מסך התנאים המסחריים. רשות: מטען בלי `commercial` תקין, והמסך מוסתר.

    כשהוא קיים הוא נבדק במלואו, כי שדה שגוי כאן אינו נראה כשגיאה: הטבלה
    פשוט מציגה שורה ריקה או ערך שאינו מתאים למקור, ואיש אינו יודע שחסר.
    """
    c = data.get("commercial")
    if c is None:
        return
    if not isinstance(c, dict):
        r.err("commercial", "commercial חייב להיות אובייקט עם fields ו-rows"); return
    fields = c.get("fields")
    rows = c.get("rows")
    if not isinstance(fields, list) or not fields:
        r.err("commercial.fields", "חסר מערך fields, ובלעדיו אין כותרות לטבלה"); return
    if not isinstance(rows, list):
        r.err("commercial.rows", "rows חייב להיות מערך"); return
    keys = set()
    for i, f in enumerate(fields):
        if not isinstance(f, dict) or not f.get("key") or not f.get("label"):
            r.err("commercial.fields[%d]" % i, "לכל תנאי נדרשים key ו-label")
        else:
            if f["key"] in keys:
                r.err("commercial.fields[%d]" % i, "מפתח כפול: %s" % f["key"])
            keys.add(f["key"])
    for i, row in enumerate(rows):
        w = "commercial.rows[%d]" % i
        if not isinstance(row, dict):
            r.err(w, "שורה חייבת להיות אובייקט"); continue
        for k in COMMERCIAL_ROW:
            if k not in row:
                r.err(w, "חסר שדה %s" % k)
        if row.get("field") and row["field"] not in keys:
            r.err(w, "field=%s אינו מופיע ב-fields" % row["field"])
        if row.get("src") and sources and row["src"] not in sources:
            r.err(w, "src=%s אינו מופיע ב-sources" % row["src"])
        if row.get("found") and not str(row.get("quote") or "").strip():
            r.warn(w, "סומן found בלי ציטוט; המגירה תיפתח ריקה")
        if row.get("found") and not str(row.get("ref") or "").strip():
            r.warn(w, "סומן found בלי מספר סעיף")


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

    # פס הבסיס: בלעדיו הדף אינו אומר על כמה הסכמים הפלייבוק נשען, והקורא
    # מניח שהוא נשען על הרבה (`dashboard_spec.md`, "פס הבסיס")
    bp = meta.get("build_path")
    if not isinstance(bp, dict):
        r.warn("meta", "meta.build_path חסר. פס הבסיס לא יוצג, והדף לא יאמר "
                       "על כמה הסכמים הפלייבוק נשען")
    else:
        if not isinstance(bp.get("n"), int):
            r.err("meta.build_path", "n חסר או אינו מספר. הוא מספר ההסכמים אחרי "
                                     "ניקוי כפילויות, ואינו מספר הקבצים בתיקייה")
        check_enum(r, "meta.build_path", "path", bp.get("path"), "build_path.path")
        if isinstance(bp.get("n"), int) and bp.get("path"):
            n, path = bp["n"], bp["path"]
            if n == 0 and path != "market_built":
                r.err("meta.build_path", "אין הסכמים, ולכן המסלול חייב להיות market_built")
            if n >= 7 and path != "own":
                r.err("meta.build_path", "ב-%d הסכמים המסלול הוא own, "
                                         "והבחירה בין שוק להסכמים אינה נשאלת" % n)
            if n > 0 and path == "market_built":
                r.err("meta.build_path", "יש %d הסכמים, ולכן המסלול אינו market_built" % n)

    # כיסוי הסעיפים: בלעדיו אין בדף תשובה לשאלה אם סעיף נשר
    cov = data.get("coverage")
    if not isinstance(cov, dict):
        r.warn("coverage", "coverage חסר. פאנל כיסוי הסעיפים לא יוצג")
    else:
        for f in ("units", "topic_units", "technical_units"):
            if not isinstance(cov.get(f), int):
                r.warn("coverage", "coverage.%s חסר או אינו מספר, והמספר יוצג כמקף" % f)
        items = cov.get("technical_items")
        if not isinstance(items, list):
            r.warn("coverage", "technical_items חסר. רשימת הסעיפים הטכניים לא תוצג")
        else:
            for i, it in enumerate(items):
                w = "coverage.technical_items[%d]" % i
                if not isinstance(it, dict):
                    r.err(w, "אינו אובייקט")
                    continue
                check_enum(r, w, "code", it.get("code"), "technical_code")
                if not (it.get("reason") or "").strip():
                    r.warn(w, "אין נימוק. הסעיף יוצג בלי הסבר למה אין לו משמעות")

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
        if (s or {}).get("kind") == "internal":
            # מי כתב את ההסכם משנה את משמעות הראיה: נוסח שהצד שכנגד כתב אינו
            # מלמד על המדיניות שלנו כמו נוסח שיצא מהנייר שלנו.
            check_enum(r, where, "paper", (s or {}).get("paper"), "source.paper",
                       required=False)
            if not (s or {}).get("paper"):
                r.warn(where, "paper חסר. לא יוצג אם ההסכם על הנייר שלנו או של הצד שכנגד")

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
        check_enum(r, where, "track", c.get("track"), "cite.track", required=False)
        if not c.get("track"):
            r.warn(where, "track חסר. הציטוט לא ישויך לעמדה, ולא ייכנס לספירת "
                          "ההסכמים ולאחוז שמוצגים בה")
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

    books = [b for b in (data.get("playbooks") or []) if b.get("id")]
    if len(data.get("playbooks") or []) > 1 and not books:
        r.err("playbooks", "יש יותר מפלייבוק אחד ואין להם id. בלי מזהה אי אפשר "
                           "לשייך סעיפים ואי אפשר לבורר לעבוד")
    if len(books) > 1:
        known = set(b["id"] for b in books)
        loose = [x.get("id") for x in (data.get("rules") or []) if not x.get("pb")]
        if loose:
            r.err("rules", "יש %d פלייבוקים, ו-%d סעיפים בלי שדה pb. סעיף בלי שיוך "
                           "יוצג בכל משפחה, ומדיניות ממשפחה אחת תיראה כאילו היא של אחרת"
                  % (len(books), len(loose)))
        for x in (data.get("rules") or []):
            if x.get("pb") and x["pb"] not in known:
                r.err("rules[%s]" % x.get("id"), "pb %r אינו קיים ב-playbooks" % x["pb"])
        shelves = data.get("books") or {}
        for b in books:
            # בדף של כמה פלייבוקים כל סוג הוא ספר שלם ב-books{}, והסעיפים
            # שבשורש הם רק של הסוג שנפתח ראשון
            pool = (shelves.get(b["id"]) or {}).get("rules") if shelves else data.get("rules")
            if not any(x.get("pb") == b["id"] for x in (pool or [])):
                r.warn("playbooks[%s]" % b["id"],
                       "אין בקובץ אף סעיף של הפלייבוק הזה. הבורר יציג מסך ריק מוסבר")
        for bid in shelves:
            if bid not in known:
                r.err("books[%s]" % bid, "ספר שאין לו שורה ב-playbooks, ולכן אין אליו מעבר בבורר")

    tracked = set()
    for c in data.get("cites") or []:
        if c.get("track"):
            for rid in c.get("rules") or []:
                tracked.add((rid, c["track"]))

    seen_rule = set()
    for i, rule in enumerate(data.get("rules") or []):
        rid = rule.get("id") or "?"
        where = "rules[%d] (%s)" % (i, rid)
        if rid in seen_rule:
            r.err(where, "מזהה הכלל %r חוזר" % rid)
        seen_rule.add(rid)
        check_enum(r, where, "kind", rule.get("kind"), "rule.kind", required=False)
        if not rule.get("they"):
            r.warn(where, "they חסר. הכרטיס 'מה הצד שכנגד ירצה' לא יוצג, ועורך הדין "
                          "יראה רק את הצד שלנו")
        for j, n in enumerate(rule.get("norms") or []):
            for f in ("law", "ref", "meaning"):
                if not n.get(f):
                    r.err("%s norms[%d]" % (where, j),
                          "%s חסר. שורת המקור הנורמטיבי תוצג חלקית" % f)
        if not rule.get("kind"):
            r.warn(where, "kind חסר. הסעיף לא ישויך למשפטי או למסחרי, והסינון לפי "
                          "סוג הסעיף לא יראה אותו")
        # עמדה בלי ציטוט אינה בעיה כשהיא מצהירה על מקור אחר: התגית נקבעת
        # לפי `basis` ו-`label`, ולא לפי היעדר ציטוטים (`dashboard_spec.md`,
        # "שדות המטען שהמבנה הזה מחייב"). עמדה בלי ציטוט ובלי מקור מוצהר
        # היא הנחה של המערכת, ועליה מזהירים
        for t in LIGHTS:
            band = (rule.get("tl") or {}).get(t) or {}
            if (rid, t) in tracked or band.get("basis") or band.get("label"):
                continue
            r.warn(where, "אין ציטוט משויך לעמדה ה%s ואין לה מקור מוצהר. היא תוצג "
                          "כהנחה של המערכת ולא כראיה מהתיקייה"
                          % {"green": "ירוקה", "yellow": "צהובה", "red": "אדומה"}[t])
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

    check_commercial(r, data, sources)


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
    # כל ספר הוא פלייבוק שלם שהדף מציג לבד כשבוחרים בו, ולכן כל אחד נבדק
    # בדיוק כמו דף של פלייבוק אחד
    for bid, book in sorted((data.get("books") or {}).items()):
        sub = dict(book)
        sub["playbooks"] = data.get("playbooks") or []
        sub.pop("books", None)
        br = validate(sub)
        r.errors += [("books[%s].%s" % (bid, w), m) for w, m in br.errors]
        r.warns += [("books[%s].%s" % (bid, w), m) for w, m in br.warns
                    if not w.startswith("playbooks[")]
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
