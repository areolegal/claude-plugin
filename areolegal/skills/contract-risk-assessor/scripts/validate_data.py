# -*- coding: utf-8 -*-
"""מאמת את risk-register.json מול הסכמה שהתבנית יודעת להציג, לפני ההזרקה.

הרציונל: התבנית אינה נקראת להקשר, ולכן ערך שאינו מוכר לה אינו מתריע.
הסקריפט רץ, הקובץ נוצר, ומסך שלם מוצג ריק או נופל לברירת מחדל שגויה.

שימוש:
  python3 validate_data.py --data risk-register.json [--strict]
"""
import argparse
import io
import json
import re
import sys

ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")

LENSES = ["legal", "commercial", "operational", "economic", "reputational", "regulatory"]

ENUMS = {
    "meta.scope": {"playbook", "deal"},
    "coverage.status": {"findings", "none_found", "not_checked"},
    "risk.category": {"legal", "business", "operational", "reputational", "regulatory"},
    "risk.certainty": {"fact", "assessment", "hypothesis"},
    "risk.mitigation_channel": {"internal", "negotiation"},
    "decision.status": {"open", "mitigating", "accepted"},
    "control.type": {"contractual", "operational", "insurance", "structural"},
    "mitigation.feasibility": {"high", "medium", "low"},
    "research.mode": {"documents_only", "official", "extended"},
    "defect.type": {"contradiction", "ambiguity", "missing_annex", "missing_agreement",
                    "undefined_term", "inconsistent_term", "broken_reference",
                    "precedence_missing", "version_mismatch", "language_mismatch",
                    "leftover_text", "blank_field"},
    "external.category": {"counterparty_stability", "regulatory_change", "change_of_control",
                          "concentration", "technology", "market", "force_majeure",
                          "third_party", "reputation"},
    "dispute_likelihood": {"high", "medium", "low"},
    "docAccess.mode": {"local", "connector", "base", "none"},
}

TOP_LEVEL = ["meta", "coverage", "risks", "document_defects", "scenarios",
             "external_risks", "dangerous_combinations", "vague_terms", "back_to_back_gaps"]


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


def check_scale(r, where, label, value):
    if not isinstance(value, int) or not 1 <= value <= 5:
        r.err(where, "%s חייב להיות מספר שלם בין 1 ל-5 לפי הרובריקה, ולא %r" % (label, value))
        return False
    return True


def validate(data):
    r = Report()
    for k in TOP_LEVEL:
        if k not in data:
            r.err("שורש הקובץ", "המפתח %r חסר. התבנית קוראת אותו, והיעדרו מרוקן מסך" % k)

    meta = data.get("meta") or {}
    if not meta.get("company"):
        r.err("meta", "meta.company חסר. שם החברה מוצג בכותרת בכל מסך")
    check_enum(r, "meta", "scope", meta.get("scope"), "meta.scope")
    check_date(r, "meta", "generated_at", meta.get("generated_at"), required=True)
    check_date(r, "meta", "last_updated", meta.get("last_updated"))
    if meta.get("scope") == "deal" and not meta.get("transaction_id"):
        r.err("meta", "scope הוא deal אך transaction_id ריק. בלעדיו לא ניתן לקשר את המרשם לעסקה")
    if meta.get("scope") == "playbook" and meta.get("transaction_id"):
        r.err("meta", "scope הוא playbook אך קיים transaction_id. "
                      "מרשם ברמת המדיניות אינו שייך לעסקה מסוימת")
    if not meta.get("source_ref"):
        r.err("meta", "source_ref חסר. לא יהיה ידוע מה נסרק")
    acc = meta.get("docAccess") or {}
    if acc:
        check_enum(r, "meta.docAccess", "mode", acc.get("mode"), "docAccess.mode", required=False)

    res = data.get("research") or {}
    if res:
        check_enum(r, "research", "mode", res.get("mode"), "research.mode", required=False)

    # כיסוי שש העדשות: חובה מוחלטת
    cov = {c.get("lens"): c for c in data.get("coverage") or []}
    for lens in LENSES:
        if lens not in cov:
            r.err("coverage", "העדשה %r אינה מופיעה בבלוק הכיסוי. "
                              "כל שש העדשות חייבות להצהיר על מצבן, וזהו כשל מסירה" % lens)
    for i, c in enumerate(data.get("coverage") or []):
        where = "coverage[%d] (%s)" % (i, c.get("lens"))
        if c.get("lens") not in LENSES:
            r.err(where, "העדשה %r אינה מוכרת. העדשות הן: %s" % (c.get("lens"), ", ".join(LENSES)))
        check_enum(r, where, "status", c.get("status"), "coverage.status")
        if c.get("status") == "not_checked" and not c.get("note"):
            r.err(where, "עדשה שלא נבדקה חייבת נימוק בשדה note")

    risk_ids = set()
    for i, k in enumerate(data.get("risks") or []):
        where = "risks[%d] (%s)" % (i, k.get("name", "ללא שם"))
        rid = k.get("id")
        if not rid:
            r.err(where, "id חסר")
        if rid in risk_ids:
            r.err(where, "מזהה הסיכון %r חוזר" % rid)
        risk_ids.add(rid)
        if not k.get("name"):
            r.err(where, "name חסר. השורה בטבלה תוצג ריקה")
        lenses = k.get("lens") or []
        if not isinstance(lenses, list) or not lenses:
            r.err(where, "lens חייב להיות מערך ובו עדשה אחת לפחות")
        else:
            for L in lenses:
                if L not in LENSES:
                    r.err(where, "העדשה %r אינה מוכרת" % L)
        check_enum(r, where, "category", k.get("category"), "risk.category")
        check_enum(r, where, "certainty", k.get("certainty"), "risk.certainty")
        check_enum(r, where, "mitigation_channel", k.get("mitigation_channel"),
                   "risk.mitigation_channel", required=False)
        for band in ("inherent", "residual"):
            b = k.get(band) or {}
            if not isinstance(b, dict):
                r.err(where, "%s חסר או אינו אובייקט" % band)
                continue
            ok_s = check_scale(r, where + "." + band, "severity", b.get("severity"))
            ok_l = check_scale(r, where + "." + band, "likelihood", b.get("likelihood"))
            if ok_s and ok_l:
                expected = b["severity"] * b["likelihood"]
                if b.get("score") != expected:
                    r.err(where + "." + band,
                          "score הוא %r אך המכפלה היא %d. מטריצת החום תמקם את הסיכון במקום שגוי"
                          % (b.get("score"), expected))
        inh, resd = k.get("inherent") or {}, k.get("residual") or {}
        if isinstance(inh.get("score"), int) and isinstance(resd.get("score"), int):
            if resd["score"] > inh["score"]:
                r.err(where, "הסיכון השיורי (%d) גבוה מהגולמי (%d). "
                             "בקרה אינה יכולה להגדיל סיכון" % (resd["score"], inh["score"]))
        for j, c in enumerate(k.get("controls") or []):
            check_enum(r, "%s.controls[%d]" % (where, j), "type", c.get("type"),
                       "control.type", required=False)
        mit = k.get("mitigation") or {}
        if mit:
            check_enum(r, where + ".mitigation", "feasibility", mit.get("feasibility"),
                       "mitigation.feasibility", required=False)
        dec = k.get("decision")
        if isinstance(dec, dict):
            check_enum(r, where + ".decision", "status", dec.get("status"),
                       "decision.status", required=False)
            check_date(r, where + ".decision", "decided_at", dec.get("decided_at"))
        anchors = k.get("anchors") or []
        if not anchors and k.get("certainty") != "hypothesis":
            r.err(where, "אין עוגן (anchors ריק), ולכן certainty חייב להיות hypothesis. "
                         "קביעה בלי מקור אינה מוצגת כעובדה")
        for j, an in enumerate(anchors):
            if not an.get("quote"):
                r.warn("%s.anchors[%d]" % (where, j), "quote ריק. הערת השוליים תיפתח ריקה")

    for i, c in enumerate(data.get("coverage") or []):
        for rid in c.get("risk_ids") or []:
            if rid not in risk_ids:
                r.err("coverage[%d]" % i, "מפנה לסיכון %r שאינו קיים" % rid)

    for i, d in enumerate(data.get("document_defects") or []):
        where = "document_defects[%d] (%s)" % (i, d.get("title", ""))
        check_enum(r, where, "type", d.get("type"), "defect.type")
        check_scale(r, where, "severity", d.get("severity"))
        if not d.get("title"):
            r.err(where, "title חסר")
        locs = d.get("locations") or []
        if len(locs) < 1:
            r.err(where, "אין אף מיקום. ליקוי בלי מיקום אינו ניתן לאיתור")
        if d.get("type") == "contradiction" and len(locs) < 2:
            r.err(where, "סתירה מחייבת לפחות שני מיקומים, אחרת אין בין מה למה")

    for i, s in enumerate(data.get("scenarios") or []):
        where = "scenarios[%d] (%s)" % (i, s.get("name", ""))
        check_scale(r, where, "severity", s.get("severity"))
        if not s.get("trigger"):
            r.err(where, "trigger חסר. לא יהיה ברור מה מפעיל את התרחיש")
        ex = s.get("exposure") or {}
        if ex.get("dispute_likelihood"):
            check_enum(r, where + ".exposure", "dispute_likelihood",
                       ex.get("dispute_likelihood"), "dispute_likelihood", required=False)
        if s.get("contract_silent") and not s.get("silence_detail"):
            r.err(where, "contract_silent הוא true אך silence_detail ריק. "
                         "יש לפרט מה בדיוק ההסכם אינו מסדיר")

    for i, e in enumerate(data.get("external_risks") or []):
        where = "external_risks[%d]" % i
        check_enum(r, where, "category", e.get("category"), "external.category")
        check_scale(r, where, "severity", e.get("severity"))
        check_scale(r, where, "likelihood", e.get("likelihood"))
        ver = e.get("verification") or {}
        if ver.get("checked") and not (ver.get("sources") or []):
            r.err(where, "verification.checked הוא true אך אין מקורות. "
                         "אין לקבוע ממצא על צד שכנגד בלי מקור")

    for i, c in enumerate(data.get("dangerous_combinations") or []):
        where = "dangerous_combinations[%d]" % i
        ids = c.get("risk_ids") or []
        if len(ids) < 2:
            r.err(where, "צירוף מחייב שני סיכונים לפחות")
        for rid in ids:
            if rid not in risk_ids:
                r.err(where, "מפנה לסיכון %r שאינו קיים" % rid)
        if not c.get("why_dangerous_together"):
            r.err(where, "why_dangerous_together חסר. בלעדיו הצירוף אינו מסביר דבר")

    if not (data.get("risks") or []):
        r.err("risks", "אין אף סיכון. הדוח יוצג ריק")
    if len(data.get("risks") or []) < 8:
        r.warn("risks", "פחות מ-8 סיכונים, ולכן מטריצת החום לא תוצג. זו התנהגות מכוונת של התבנית")

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
