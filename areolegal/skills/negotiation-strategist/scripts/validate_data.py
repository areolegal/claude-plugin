# -*- coding: utf-8 -*-
"""מאמת את strategy-data.json מול הסכמה שהתבנית יודעת להציג, לפני ההזרקה.

הרציונל: התבנית אינה נקראת להקשר, ולכן ערך שאינו מוכר לה אינו מתריע.
הסקריפט רץ, הקובץ נוצר, ומסך שלם מוצג ריק.

הסכמה המחייבת כתובה ב-strategist-main.md ("סכמת strategy-data.json"), ו-FIELDS שלהלן הוא אותה סכמה בקוד:
כל שדה שהתבנית קוראת נבדק לטיפוסו, ושדה שאינה קוראת הוא אזהרה. בנוסף: כלל both בשפות, ומייל
הסיכום לצד השני, שנבנה רק מ-outbound.items עם approved: true (קבצים ישנים: companion.mail_items עם
share_safe: true) ולעולם לא משורה פנימית. הפרדת פנימי וחיצוני היא מבנית (external_view, leak_check, ראו מטה);
הצעת שינוי (proposal) קשורה לגרסת בסיס, ומרחב התרגול (practice) אינו כותב מצב.

שימוש:
  python3 validate_data.py --data strategy-data.json [--strict]
"""
import argparse
import io
import json
import re
import sys

for _s in (sys.stdout, sys.stderr):  # עברית בקונסולה שאינה UTF-8 (cp1252): בלי UnicodeEncodeError
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):   # לא TextIOWrapper (לכידה בבדיקות, pythonw)
        pass

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

ENUMS = {
    "risk.severity": {"critical", "high", "medium", "low"},
    "node.side": {"us", "them"},
    # המסלול של שורה בעץ התגובות: סולם ירוק-צהוב-אדום (prep_center_spec.md, ד). התבנית צובעת לפי
    # LVL שלה. ערך שהתבנית אינה מכירה (hard, soft, open, bridge) מוצג באפור, ולכן הבודק והתבנית מתואמים
    "node.level": {"green", "yellow", "red"},
    # מקור ניסוח הגשר (כלל 13): הנוסח שלהם, הפלייבוק, או הצעה של המערכת
    "bridge.source": {"their_wording", "playbook", "system_proposal"},
    "dialogue.who": {"us", "them"},
    "docAccess.mode": {"local", "connector", "base", "none"},
    # שפת התוצר: התבנית מציגה עברית RTL או אנגלית LTR. both: המרכז בשפת
    # display_language, ומה שיוצא לצד השני בשפת ההסכם (agreement_language)
    "meta.deliverable_language": {"he", "en", "both"},
    "meta.display_language": {"he", "en"},
    "meta.agreement_language": {"he", "en"},
    # סוג הנייר, מקובץ המצב של הנושא ונותן (n1b-learning.md, שלב א.6)
    "meta.paper_type": {"negotiable", "tender_pre_bid", "tender_awarded", "standard_form_online"},
}

TOP_LEVEL = ["meta", "counters", "clauses", "risks", "plan", "companion", "footnotes"]
LINES = ("red", "yellow", "bridge")

# כל שדה שהתבנית קוראת, לפי מקומו (strategist-main.md, "סכמת strategy-data.json"). s: טקסט או מספר, i: מספר שלם,
# l: מערך, o: אובייקט, b: true/false, n: מערך מספרי הערות שוליים, ls: מערך מחרוזות. שדה שאינו כאן אינו
# מוצג בתבנית, ולכן הוא אזהרה: לרוב זה שם שדה ששונה
FIELDS = {
    "": {"meta": "o", "counters": "o", "changed": "l", "timeline": "l", "plan": "o", "clauses": "l",
         "risks": "l", "companion": "o", "footnotes": "l", "outbound": "o", "proposal": "o", "practice": "o"},
    "meta": {"company": "s", "counterparty": "s", "agreement": "s", "transaction_id": "s", "generated_at": "s",
             "last_updated": "s", "round_number": "i", "sharing": "s", "publishTarget": "s",
             "deliverable_language": "s", "display_language": "s", "agreement_language": "s", "lang": "s",
             "docAccess": "o", "status": "o", "health": "o", "power": "o", "branding": "o", "paper_type": "s"},
    "meta.docAccess": {"mode": "s", "baseUrl": "s"},
    "meta.status": {"text": "s", "source": "s", "date": "s", "ref": "s"},
    "meta.health": {"label": "s", "note": "s"},
    "meta.power": {"label": "s", "regime": "s", "rationale": "s", "leverage": "s", "constraint": "s"},
    "meta.branding": {"logo": "s", "theme": "o"},
    "meta.branding.theme": {"primary_light": "s", "secondary_light": "s", "soft_light": "s", "on_light": "s",
                            "primary_dark": "s", "secondary_dark": "s", "soft_dark": "s", "on_dark": "s"},
    "counters": {"aligned": "i", "disputed": "i", "redline": "i"},
    "changed[]": {"what": "s", "note": "s"},
    "timeline[]": {"date": "s", "event": "s", "source": "s"},
    "plan": {"next_move": "o", "order": "l", "give": "l", "ask": "l"},
    "plan.next_move": {"title": "s", "why": "s"},
    "plan.order[]": {"step": "s", "why": "s"},
    "plan.give[]": {"what": "s", "why": "s"},
    "plan.ask[]": {"what": "s", "why": "s"},
    "clauses[]": {"id": "s", "title": "s", "segment": "s", "playbook": "o", "lines": "o", "bargain": "o",
                  "tree": "l", "dialogue": "l", "refs": "n"},
    "clauses[].playbook": {"position": "s", "why": "s"},
    "clauses[].lines": {"red": "o", "yellow": "o", "bridge": "o"},
    "clauses[].lines.red": {"what": "s", "why": "s"},
    "clauses[].lines.yellow": {"what": "s", "conditions": "s"},
    "clauses[].lines.bridge": {"wording": "s", "why": "s", "source": "s"},
    "clauses[].bargain": {"their_open": "s", "our_counter": "s", "their_refusal": "s", "midpoints": "l"},
    "clauses[].bargain.midpoints[]": {"point": "s", "criterion": "s", "in_return": "s"},
    "clauses[].tree[]": {"level": "s", "side": "s", "text": "s", "emotion": "s", "risk": "s", "refs": "n"},
    "clauses[].dialogue[]": {"who": "s", "text": "s", "note": "s"},
    "risks[]": {"id": "s", "title": "s", "severity": "s", "mitigation": "s", "clause_id": "s", "refs": "n"},
    "companion": {"pocket": "ls", "redlines": "ls", "donot": "ls", "briefing": "ls", "pause_line": "s",
                  "mail_subject": "s", "mail_items": "l"},
    "companion.mail_items[]": {"text": "s", "share_safe": "b", "clause_id": "s"},
    # נוסח לצד השני: המקטע היחיד שיוצא החוצה. approved: true מפורש; derived_from ו-approved_by נשארים פנימיים
    "outbound": {"subject": "s", "items": "l"},
    "outbound.items[]": {"text": "s", "approved": "b", "approved_by": "s", "derived_from": "ls"},
    # הצעת שינוי לנושא ונותן (S-05): קשורה לגרסת בסיס, לסוגיות ולתלויות. אינה הסכמה בפועל
    "proposal": {"base": "o", "changes": "l", "status": "s"},
    "proposal.base": {"round_number": "i", "state_updated": "s", "version": "s"},
    "proposal.changes[]": {"id": "s", "clause_id": "s", "issue": "s", "what": "s", "kind": "s", "depends_on": "ls"},
    # מרחב תרגול נפרד: ויתור בסימולציה אינו משנה הסכם, פלייבוק, סבב או מצב
    "practice": {"space": "s", "writes_state": "b", "base_round": "i", "sessions": "l"},
    "practice.sessions[]": {"id": "s", "clause_id": "s", "base_round": "i", "concessions": "l", "note": "s"},
    "practice.sessions[].concessions[]": {"what": "s", "simulated": "b"},
    "footnotes[]": {"n": "i", "clause": "s", "quote": "s", "doc": "s", "date": "s", "page": "s", "file": "s",
                    "webUrl": "s", "urlSource": "s"},
}

# שורה שנפתחת בסימון פנימי לעולם אינה יוצאת לצד השני. אותו ביטוי כמו INTERNAL_RE בתבנית
INTERNAL = re.compile(u"^[\\s‎‏‪-‮⁦-⁩]*\\[\\s*(פנימי|internal)\\s*\\]", re.I)
HEB = re.compile(u"[֐-׿]")
LATIN = re.compile(r"[A-Za-z]")


def text_lang(s):
    """השפה הגסה של טקסט: he כשיש בו אותיות עבריות, en כשיש בו רק לטיניות, None כשאין אותיות."""
    s = s or ""
    if HEB.search(s):
        return "he"
    return "en" if LATIN.search(s) else None


def type_ok(kind, v):
    if kind == "s":
        return isinstance(v, (str, int, float)) and not isinstance(v, bool)
    if kind == "i":
        return isinstance(v, int) and not isinstance(v, bool)
    if kind in ("l", "ls", "n"):
        if not isinstance(v, list):
            return False
        if kind == "ls":
            return all(isinstance(x, str) for x in v)
        if kind == "n":
            return all(isinstance(x, int) and not isinstance(x, bool) for x in v)
        return True
    if kind == "o":
        return isinstance(v, dict)
    if kind == "b":
        return isinstance(v, bool)
    return True


KIND_NAME = {"s": "טקסט", "i": "מספר שלם", "l": "מערך", "ls": "מערך מחרוזות", "n": "מערך מספרי הערות שוליים",
             "o": "אובייקט", "b": "true או false"}


def check_shape(r, data):
    """טיפוס כל שדה מוכר, ואזהרה על שדה שהתבנית אינה קוראת. None נחשב שדה ריק."""
    def walk(obj, key, where):
        spec = FIELDS.get(key)
        if spec is None or not isinstance(obj, dict):
            return
        for f, v in obj.items():
            w = "%s.%s" % (where, f) if where else f
            if f not in spec:
                r.warn(where or "שורש הקובץ", "השדה %r אינו בסכמה, והתבנית אינה מציגה אותו. "
                                               "שם שדה ששונה? (strategist-main.md, סכמת strategy-data.json)" % f)
                continue
            if v is None:
                continue
            kind = spec[f]
            if not type_ok(kind, v):
                r.err(w, "חייב להיות %s, ולא %s" % (KIND_NAME[kind], type(v).__name__))
                continue
            sub = ("%s.%s" % (key, f)) if key else f
            if kind == "o":
                walk(v, sub, w)
            elif kind == "l" and (sub + "[]") in FIELDS:
                for j, x in enumerate(v):
                    if not isinstance(x, dict):
                        r.err("%s[%d]" % (w, j), "חייב להיות אובייקט, ולא %s" % type(x).__name__)
                        continue
                    walk(x, sub + "[]", "%s[%d]" % (w, j))
    walk(data, "", "")


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
    check_shape(r, data)
    for f in ("deliverable_language", "display_language", "agreement_language", "paper_type"):
        check_enum(r, "meta", f, meta.get(f), "meta." + f, required=False)
    # נייר שאינו פתוח למשא ומתן (מכרז, תנאים אחידים): אין סולם ויתורים ואין מיקוח. התבנית מסתירה אותם, ולכן
    # נתונים כאלה הם סימן שההכנה נבנתה כמו למשא ומתן רגיל
    if meta.get("paper_type") in ("tender_pre_bid", "tender_awarded", "standard_form_online"):
        if ((data.get("plan") or {}).get("give")):
            r.warn("plan.give", "סוג הנייר %s: אין ויתורים בנייר שאינו פתוח למשא ומתן. ההכנה היא לבירורים "
                                "ולהחלטה לפני חתימה" % meta.get("paper_type"))
        if any((c.get("bargain") or {}).get("midpoints") for c in data.get("clauses") or []):
            r.warn("clauses", "סוג הנייר %s: אין נקודות פשרה בנייר שאינו פתוח למשא ומתן" % meta.get("paper_type"))
    dl = meta.get("deliverable_language")
    agl = meta.get("agreement_language")
    if dl == "both":
        # both: המרכז וכרטיס הכיס בשפת הממשק, וחומר שיוצא לצד השני בשפת ההסכם
        if not agl:
            r.err("meta", "deliverable_language הוא both בלי agreement_language. בלעדיו אין לדעת "
                          "באיזו שפה נכתבים מייל הסיכום והמשפטים שנאמרים לצד השני")
        if not meta.get("display_language"):
            r.warn("meta", "deliverable_language הוא both בלי display_language. המרכז ייבנה בעברית")
    elif not agl:
        r.warn("meta", "agreement_language חסר. מייל הסיכום ייכתב בשפת המרכז, ולא בשפת ההסכם")
    acc = meta.get("docAccess") or {}
    if acc:
        check_enum(r, "meta.docAccess", "mode", acc.get("mode"), "docAccess.mode", required=False)
        if acc.get("mode") == "base" and not acc.get("baseUrl"):
            r.warn("meta.docAccess", "mode הוא base בלי baseUrl. לא ייגזרו קישורים למסמכים")
    pw = meta.get("power") or {}
    if pw and not pw.get("label"):
        r.warn("meta.power", "label ריק. כרטיס מאזן הכוחות אינו מוצג כלל")
    for i, x in enumerate(data.get("changed") or []):
        if isinstance(x, dict) and not x.get("what"):
            r.err("changed[%d]" % i, "what חסר. השורה תוצג ריקה")

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
            if L == "bridge":
                # כלל 13: לכל גשר יש מקור. גשר בלי מקור אינו מראה אם נבדק מול הנוסח שלהם
                if band.get("source") in (None, ""):
                    r.warn("%s.lines.bridge" % where, "source חסר. לכל גשר נרשם מקור: their_wording, "
                                                       "playbook או system_proposal")
                else:
                    check_enum(r, "%s.lines.bridge" % where, "source", band.get("source"), "bridge.source")
        check_refs(where, c.get("refs"))
        for j, n in enumerate(c.get("tree") or []):
            nw = "%s.tree[%d]" % (where, j)
            check_enum(r, nw, "side", n.get("side"), "node.side")
            check_enum(r, nw, "level", n.get("level"), "node.level", required=False)
            if not n.get("text"):
                r.err(nw, "text חסר")
            check_refs(nw, n.get("refs"))
        dlg = c.get("dialogue") or []
        off_lang = []
        for j, d in enumerate(dlg):
            dw = "%s.dialogue[%d]" % (where, j)
            check_enum(r, dw, "who", d.get("who"), "dialogue.who")
            if not d.get("text"):
                r.err(dw, "text חסר. הבועה תוצג ריקה")
            # both: משפט שלנו נאמר לצד השני, ולכן הוא בשפת ההסכם. הערת הבימוי נשארת בשפת הממשק
            elif dl == "both" and agl and d.get("who") == "us" and text_lang(str(d.get("text"))) not in (None, agl):
                off_lang.append(j)
        if off_lang:
            r.warn("%s.dialogue" % where, "deliverable_language הוא both, ו-%d משפטים שלנו אינם בשפת ההסכם (%s): "
                                          "dialogue %s. משפט שנאמר לצד השני נכתב בשפת ההסכם"
                   % (len(off_lang), agl, ", ".join(str(j) for j in off_lang)))
        if dlg and len(dlg) < 8:
            r.warn(where, "התסריט מכיל %d חילופי דברים. המפרט דורש 8 עד 12, "
                          "אחרת הוא קורא כתקציר ולא כאימון" % len(dlg))
        b = c.get("bargain") or {}
        if (b.get("our_counter") or b.get("their_refusal")) and not b.get("their_open") and not b.get("midpoints"):
            r.warn("%s.bargain" % where, "their_open חסר. בלעדיו ובלי midpoints, סימולציית המיקוח אינה מוצגת כלל")
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
    if dl == "both" and agl and cmp_.get("pause_line") and text_lang(cmp_["pause_line"]) not in (None, agl) \
            and not (agl == "en" and LATIN.search(cmp_["pause_line"])):
        r.warn("companion.pause_line", "deliverable_language הוא both, ומשפט ההפסקה אינו בשפת ההסכם (%s)" % agl)

    # מייל הסיכום יוצא לצד השני: הוא נבנה רק מ-mail_items שמסומנים
    # share_safe: true, בשפת ההסכם, ולעולם לא משורה פנימית
    internal = set()
    for k in ("pocket", "redlines", "donot", "briefing"):
        internal.update(x.strip() for x in (cmp_.get(k) or []) if isinstance(x, str))
    if isinstance(cmp_.get("pause_line"), str):
        internal.add(cmp_["pause_line"].strip())
    for c in data.get("clauses") or []:
        L = c.get("lines") or {}
        for band, key in (("red", "what"), ("red", "why"), ("yellow", "what"), ("yellow", "conditions")):
            v = (L.get(band) or {}).get(key)
            if isinstance(v, str):
                internal.add(v.strip())
        for n in c.get("tree") or []:
            if isinstance(n.get("text"), str):
                internal.add(n["text"].strip())
    mail_lang = agl or (meta.get("display_language") if dl == "both" else dl) or "he"
    items = cmp_.get("mail_items") or []
    if not items:
        r.warn("companion.mail_items", "אין פריטים לצד השני. בסיס מייל הסיכום יצא עם מקום להשלמה בלבד")
    for i, m in enumerate(items):
        w = "companion.mail_items[%d]" % i
        if not isinstance(m, dict):
            continue
        t = str(m.get("text") or "").strip()
        if not t:
            r.err(w, "text חסר")
            continue
        if m.get("share_safe") is not True:
            r.err(w, "share_safe אינו true. פריט למייל הסיכום מסומן במפורש share_safe: true, "
                     "ובלעדיו התבנית אינה מכניסה אותו למייל")
        if INTERNAL.match(t):
            r.err(w, "הפריט מסומן פנימי ([פנימי] או [internal]). שורה פנימית לעולם אינה נכנסת למייל לצד השני")
        if t in internal:
            r.err(w, "הפריט זהה לשורה פנימית (כרטיס הכיס, קו אדום, מדרגת נסיגה, תדריך או עץ התגובות). "
                     "מייל לצד השני נכתב מחדש, ואינו מעתיק שורה פנימית")
        if text_lang(t) not in (None, mail_lang):
            r.warn(w, "הפריט אינו בשפת ההסכם (%s). מייל הסיכום נכתב בשפת ההסכם" % mail_lang)
        cid = m.get("clause_id")
        if cid and cid not in clause_ids:
            r.err(w, "clause_id %r אינו קיים ברשימת הסעיפים" % cid)
    subj = cmp_.get("mail_subject")
    if isinstance(subj, str) and subj.strip():
        if INTERNAL.match(subj):
            r.err("companion.mail_subject", "הנושא מסומן פנימי, ולא ייכנס למייל")
        elif text_lang(subj) not in (None, mail_lang):
            r.warn("companion.mail_subject", "הנושא אינו בשפת ההסכם (%s)" % mail_lang)
    elif agl and agl != (meta.get("display_language") if dl == "both" else (dl or "he")):
        r.warn("companion.mail_subject", "mail_subject חסר, ושפת ההסכם שונה משפת המרכז. "
                                         "נושא המייל ייצא עם מקום להשלמה")

    for i, e in enumerate(data.get("timeline") or []):
        where = "timeline[%d]" % i
        check_date(r, where, "date", e.get("date"), required=True)
        if not e.get("event"):
            r.err(where, "event חסר")
        if not e.get("source"):
            r.err(where, "source חסר. אירוע בציר הזמן נושא תמיד את מקורו")

    if not (data.get("clauses") or []):
        r.warn("clauses", "אין סעיפים במחלוקת. הלשונית תוצג עם הודעת ריק מכוונת")

    check_sections(r, data, clause_ids)
    return r


# ---------------------------------------------------------------------------
# הפרדה מבנית בין הכנה פנימית להצעה חיצונית (S-06) ובין הצעת שינוי לסימולציה (S-05)
#
# סיווג נפרד: קובץ ההכנה (meta, plan, clauses, risks, timeline, footnotes), כרטיס השיחה (companion),
# חומר התרגול (clauses[].tree, clauses[].dialogue, practice) ונוסח לצד השני (outbound). רק outbound יוצא החוצה.
# העותק החיצוני נבנה ב-external_view: רשימת היתר, לא סינון בדיעבד. מה שלא נכלל שם אינו קיים בנתוני העותק.
# בדיקת התוכן המדויק (leak_check) מחפשת בבייטים של העותק שנבנה כל מחרוזת פנימית. היא תופסת הדלפה מילולית
# בלבד: הדלפה בניסוח מחדש (פרפרזה) אי אפשר להוכיח בקוד שאינה קיימת, ולכן נשארות גם בדיקת רשימת המילים
# וסקירת עורך דין.
# ---------------------------------------------------------------------------
EXTERNAL_META = ("company", "counterparty", "agreement", "agreement_language", "generated_at")
MIN_MARKER = 12      # מחרוזת פנימית קצרה מזה אינה סמן מובחן (תוויות, קודים), ולכן אינה נבדקת
MIN_FRAGMENT = 20

# שכבה משלימה, אזהרה בלבד: מונחי משא ומתן פנימיים כלליים בנוסח שיוצא לצד השני
WORDLIST = re.compile(
    u"BATNA|walk[- ]?away|red[- ]?line|fallback|bottom line|קו אדום|מדרגת נסיגה|נקודת נסיגה|"
    u"אלטרנטיבה הטובה|גבול פנימי|תקרה פנימית|\\[\\s*(?:פנימי|internal)\\s*\\]", re.I)
FORBIDDEN_PRACTICE_KEYS = {"round_number", "counters", "status", "negotiation_state", "agreement", "playbook",
                           "plan", "clauses", "state", "round"}


def _norm(s):
    return " ".join(str(s).split())


def external_view(data):
    """הנתונים היחידים שמרכיב שמפיק טקסט לצד השני מקבל. רשימת היתר: meta חלקי, נושא ופריטים מאושרים (text בלבד).

    outbound קיים: רק פריטים עם approved: true. בלי outbound (קובץ ישן): companion.mail_items עם share_safe: true.
    שום שדה פנימי, אפילו לא derived_from או clause_id, אינו עובר."""
    meta = data.get("meta") or {}
    ob = data.get("outbound")
    items, subject = [], ""
    if isinstance(ob, dict):
        subject = ob.get("subject") if isinstance(ob.get("subject"), str) else ""
        for m in ob.get("items") or []:
            t = _norm(m.get("text")) if isinstance(m, dict) and isinstance(m.get("text"), str) else ""
            if t and m.get("approved") is True and not INTERNAL.match(t):
                items.append({"text": t})
    else:
        cmp_ = data.get("companion") or {}
        subject = cmp_.get("mail_subject") if isinstance(cmp_.get("mail_subject"), str) else ""
        for m in cmp_.get("mail_items") or []:
            t = _norm(m.get("text")) if isinstance(m, dict) and isinstance(m.get("text"), str) else ""
            if t and m.get("share_safe") is True and not INTERNAL.match(t):
                items.append({"text": t})
    if INTERNAL.match(subject or ""):
        subject = ""
    return {"meta": {k: meta[k] for k in EXTERNAL_META if isinstance(meta.get(k), str)},
            "outbound": {"subject": _norm(subject), "items": items}}


def _leaves(obj, path=""):
    if isinstance(obj, str):
        yield path, obj
    elif isinstance(obj, dict):
        for k, v in obj.items():
            for x in _leaves(v, "%s.%s" % (path, k) if path else k):
                yield x
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for x in _leaves(v, "%s[%d]" % (path, i)):
                yield x


def internal_markers(data):
    """{מחרוזת: נתיב השדה} של כל תוכן שאינו ברשימת ההיתר: שלמות, ובמחרוזות ארוכות גם קטעי משפט.
    outbound עצמו אינו סמן (הוא נוסח לצד השני), אך פריט שלא אושר הוא סמן, כי הוא אינו עובר לעותק."""
    view = external_view(data)
    allowed = set(_norm(s) for _, s in _leaves(view))
    out = {}
    for path, s in _leaves(data):
        root = path.split("[")[0].split(".")[0]
        if root == "outbound" and not path.endswith(".derived_from") and ".derived_from[" not in path:
            if _norm(s) in allowed or path.endswith((".approved_by", ".subject")):
                continue
        if s.startswith("data:") and len(s) > 500:
            continue
        n = _norm(s)
        if n in allowed:
            continue
        if len(n) >= MIN_MARKER:
            out.setdefault(n, path)
        if len(n) >= 2 * MIN_FRAGMENT:
            for frag in re.split(u"[.!?;:\\n,]+", s):
                f = _norm(frag)
                if len(f) >= MIN_FRAGMENT and f not in allowed and not any(f in a for a in allowed):
                    out.setdefault(f, path)
    return out


def _variants(s):
    out = set()
    for b in (s, s.replace(u"—", ", ").replace(u"–", "-")):
        esc = b.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        out.update((b, esc, esc.replace('"', "&quot;"),
                    json.dumps(b, ensure_ascii=False)[1:-1].replace("</", "<\\/"),
                    json.dumps(b, ensure_ascii=True)[1:-1].replace("</", "<\\/")))
    return out


def leak_check(built, data):
    """בדיקת תוכן מדויק על העותק החיצוני שנבנה (מחרוזת או בייטים): כל סמן פנימי בכל צורת קידוד.
    מחזיר רשימת נתיבי השדות הפנימיים שתוכנם נמצא. רשימה ריקה: אין הדלפה מילולית.
    אינה מוכיחה היעדר פרפרזה, ואינה תחליף לסקירה."""
    text = built.decode("utf-8", "replace") if isinstance(built, (bytes, bytearray)) else built
    collapsed = _norm(text)
    hits = []
    for marker, path in internal_markers(data).items():
        if any(v in text or v in collapsed for v in _variants(marker)):
            hits.append(path)
    return hits


def check_sections(r, data, clause_ids):
    meta = data.get("meta") or {}
    rnd = meta.get("round_number") if isinstance(meta.get("round_number"), int) else None
    markers = internal_markers(data)
    ob = data.get("outbound")
    cmp_ = data.get("companion") or {}
    legacy = [m for m in (cmp_.get("mail_items") or []) if isinstance(m, dict)]
    if isinstance(ob, dict):
        if legacy:
            r.warn("companion.mail_items", "יש גם outbound וגם mail_items ישן. הצד השני נבנה מ-outbound בלבד, "
                                           "ו-mail_items אינו יוצא")
        for i, m in enumerate(ob.get("items") or []):
            w = "outbound.items[%d]" % i
            if not isinstance(m, dict):
                continue
            t = _norm(m.get("text") or "")
            if not t:
                r.err(w, "text חסר")
                continue
            if not isinstance(m.get("approved"), bool):
                r.err(w, "approved חסר או אינו true/false. רק נוסח שאושר במפורש (true) לצד השני נכלל בעותק החיצוני")
            elif m.get("approved") is False:
                r.warn(w, "נוסח שטרם אושר (approved: false) אינו נכלל בעותק החיצוני")
            if INTERNAL.match(t):
                r.err(w, "הפריט מסומן פנימי. שורה פנימית לעולם אינה נכנסת לנוסח לצד השני")
            for mk, path in markers.items():
                if not path.startswith("outbound") and (mk in t or (t in mk and len(t) >= MIN_MARKER)):
                    r.err(w, "הנוסח מעתיק תוכן פנימי מ-%s. נוסח לצד השני נכתב מחדש ממה שאושר, "
                             "ולא מתוך נימוק פנימי" % path)
                    break
            if WORDLIST.search(t):
                r.warn(w, "בנוסח מונח של משא ומתן פנימי (בדיקת רשימת מילים משלימה). בדוק שאינו חושף עמדה")
            for cid in m.get("derived_from") or []:
                if cid not in clause_ids:
                    r.err(w, "derived_from %r אינו קיים ברשימת הסעיפים" % cid)
        subj = ob.get("subject")
        if isinstance(subj, str) and subj.strip():
            if INTERNAL.match(subj):
                r.err("outbound.subject", "הנושא מסומן פנימי")
            elif any(not p.startswith("outbound") and mk in subj for mk, p in markers.items()):
                r.err("outbound.subject", "הנושא מעתיק תוכן פנימי")
        if not (ob.get("items") or []):
            r.warn("outbound.items", "אין פריטים מאושרים לצד השני. העותק החיצוני יצא ריק")
    elif legacy:
        r.warn("companion.mail_items", "קובץ במבנה ישן: הצד השני נבנה מפריטי share_safe: true בלבד, בסינון נתונים. "
                                       "מומלץ לעבור ל-outbound.items עם approved: true")

    pr = data.get("proposal")
    if isinstance(pr, dict):
        base = pr.get("base") if isinstance(pr.get("base"), dict) else {}
        brn = base.get("round_number")
        if not isinstance(brn, int) or isinstance(brn, bool):
            r.err("proposal.base", "round_number חסר. הצעת שינוי נקשרת לגרסת בסיס של קובץ המצב")
        if not base.get("state_updated"):
            r.err("proposal.base", "state_updated חסר (last_updated של קובץ המצב בעת הקריאה). "
                                   "בלי גרסת בסיס אי אפשר לדעת אם ההצעה התיישנה")
        if rnd is not None and isinstance(brn, int) and brn != rnd:
            r.err("proposal.base", "ההצעה נשענת על סבב %s והמרכז על סבב %s. הסבב השתנה בזמן ההכנה: חובה לרענן "
                                   "(קריאה מחדש של קובץ המצב ובניית ההצעה מחדש)" % (brn, rnd))
        ids = set(ch["id"] for ch in (pr.get("changes") or []) if isinstance(ch, dict) and ch.get("id"))
        for i, ch in enumerate(pr.get("changes") or []):
            w = "proposal.changes[%d]" % i
            if not isinstance(ch, dict):
                continue
            for f in ("id", "clause_id", "what"):
                if not ch.get(f):
                    r.err(w, "%s חסר. שינוי מוצע נושא מזהה, סעיף ותוכן" % f)
            if ch.get("clause_id") and ch["clause_id"] not in clause_ids:
                r.err(w, "clause_id %r אינו קיים ברשימת הסעיפים" % ch["clause_id"])
            for d in ch.get("depends_on") or []:
                if d == ch.get("id"):
                    r.err(w, "שינוי תלוי בעצמו")
                elif d not in ids:
                    r.err(w, "depends_on %r אינו שינוי בהצעה" % d)
        if pr.get("status") not in (None, "", "proposed"):
            r.err("proposal.status", "הצעה היא תמיד proposed. קבלתה נעשית בנושא ונותן ובאישור המשתמש, לא כאן")

    pc = data.get("practice")
    if isinstance(pc, dict):
        if pc.get("writes_state") not in (None, False):
            r.err("practice.writes_state", "סימולציה אינה כותבת מצב. חייב להיות false או חסר")
        if pc.get("space") not in (None, "", "simulation"):
            r.err("practice.space", "מרחב התרגול הוא simulation בלבד")
        for k in pc:
            if k in FORBIDDEN_PRACTICE_KEYS:
                r.err("practice.%s" % k, "שדה של מצב אמיתי בתוך מרחב התרגול. תרגול אינו נושא סבב, מוני התאמה, "
                                         "סטטוס, פלייבוק או נוסח הסכם")
        for i, s in enumerate(pc.get("sessions") or []):
            if not isinstance(s, dict):
                continue
            w = "practice.sessions[%d]" % i
            for k in s:
                if k in FORBIDDEN_PRACTICE_KEYS:
                    r.err(w, "שדה %r אסור בתרגול (מצב אמיתי)" % k)
            if s.get("clause_id") and s["clause_id"] not in clause_ids:
                r.err(w, "clause_id %r אינו קיים ברשימת הסעיפים" % s["clause_id"])
            for j, c in enumerate(s.get("concessions") or []):
                if isinstance(c, dict) and c.get("simulated") is not True:
                    r.err("%s.concessions[%d]" % (w, j), "ויתור בסימולציה חייב לשאת simulated: true. "
                                                       "הוא אינו משנה הסכם, פלייבוק או מצב אמיתי")
            br = s.get("base_round")
            if rnd is not None and isinstance(br, int) and br != rnd:
                r.warn(w, "התרגול נעשה בסבב %s והמרכז בסבב %s. הסבב השתנה: התרגול התיישן וצריך רענון" % (br, rnd))


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
