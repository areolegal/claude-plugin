#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""בונה תבנית אב ושלד הסכם מקובץ Word אחד. רץ פעם אחת למשפחת הסכמים.

    python3 build_master_template.py --source "<תבנית או הסכם>.docx" \\
        --family "הסכם שירותים" --kind template|agreement \\
        --out-dir "Areo-נתונים/תבניות/הסכם שירותים" [--company "<שם החברה>"]

--kind template: קובץ שנועד להימלא. המשתנים הם השדות הריקים: קווים תחתונים,
  סוגריים מרובעים ותגיות {{...}} שכבר קיימות.
--kind agreement: הסכם שנחתם בעבר על הנייר של החברה, שמשמש שלד. בנוסף לשדות
  הריקים, גם הפרטים של העסקה ההיא הם משתנים: מספרי זיהוי, תאריכים, סכומים,
  טלפונים, דוא"ל ושם הצד שכנגד. פרטי החברה עצמה (--company) אינם משתנים.

הפלט:
  master.docx    אותו מסמך בדיוק, שבו כל משתנה הוחלף בתגית {{סוג_מספר}} במקומו.
                 הנוסח, הסגנונות, המספור והכיווניות אינם נוגעים.
  skeleton.json  המשתנים (סוג, תווית, הקשר, הערך שנמצא), הסעיפים ורצפי המספור.

**המודל אינו פותח את master.docx.** ההרצות הבאות קוראות רק את skeleton.json,
ו-fill_template.py הוא שממלא.
"""
import argparse
import datetime
import hashlib
import io
import json
import os
import re
import sys

from docx import Document
from docx.oxml.ns import qn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from docx_numbering import (assign_segments, body_segment, labelled_paragraphs,  # noqa: E402
                            replace_spans, segment_summary)

TAG_RX = re.compile(r"\{\{\s*([^{}]{1,60}?)\s*\}\}")
BLANK_RX = re.compile(r"_{2,}|\.{6,}|…{2,}")
BRACKET_RX = re.compile(r"\[(?:[^\[\]\n]{0,40})\]")
# review markers, not fields: filling one would erase the flag the lawyer must clear
MARKERS = re.compile(r"\[\s*(?:טעון בדיקת פסיקה|טעון אימות|נוסח חדש[^\]]*)\s*\]")

VALUE_PATTERNS = [
    ("מספר_זיהוי", re.compile(
        r"(?:ח\.?\s?פ\.?|ע\.?\s?מ\.?|ת\.?\s?ז\.?|מס['׳]?\s*חברה|Company\s+No\.?|Reg\.?\s+No\.?)"
        r"\s*[:\-]?\s*(\d{8,9})")),
    ("דואל", re.compile(r"([\w.+-]+@[\w-]+\.[\w.-]+)")),
    ("טלפון", re.compile(r"(?<!\d)(0\d{1,2}-?\d{3}-?\d{4}|\+972-?\d{1,2}-?\d{7})(?!\d)")),
    ("תאריך", re.compile(r"(?<!\d)(\d{1,2}[./]\d{1,2}[./](?:\d{4}|\d{2}))(?!\d)")),
    ("סכום", re.compile(
        r"((?:₪|\$|€)\s*\d[\d,]*(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s*(?:₪|ש\"ח|ש״ח|שקלים|NIS|USD|EUR|דולר))")),
]
LABEL_TYPES = [
    ("תאריך", ("ביום", "תאריך", "בחודש", "שנת", "בשנת", "מיום", "date", "dated")),
    ("מספר_זיהוי", ("ח.פ", "ח. פ", "חפ", "ע.מ", "ת.ז", "מס' חברה", "company no")),
    ("סכום", ("סך", "ש\"ח", "ש״ח", "₪", "תמורה", "שכר", "amount", "fee")),
    ("כתובת", ("מרחוב", "רחוב", "כתובת", "address")),
    ("טלפון", ("טלפון", "טל'", "phone", "tel")),
    ("דואל", ("דוא\"ל", "מייל", "email", "e-mail")),
    ("שם_צד", ("חברת", "בין", "לבין", "שם", "name", "between")),
]
COMPANY_MARK = re.compile(r"בע\"מ|בע״מ|\bLtd\b|\bInc\b|\bLLC\b|חברת\s", re.I)
BODY_START = re.compile(r"^\s*(?:הואיל|WHEREAS|R\s?E\s?C\s?I\s?T\s?A\s?L\s?S|לפיכך)", re.I)
PARTY_LEAD = re.compile(r"^\s*(?:-?\s*ב\s?י\s?ן\s?-?\s*:?|ל\s?ב\s?י\s?ן\s*:?|חברת|between\s*:?|and\s*:?)\s*", re.I)


def norm(s):
    return re.sub(r"[\s\"'״׳.,()\-]", "", s or "").lower()


FIELD_END = re.compile(r"_{2,}|\.{6,}|…{2,}|\[[^\[\]\n]{0,40}\]|\{\{[^{}]*\}\}")
SIGNING_LINE = re.compile(r"חתימה|חותמת|signature|signed\s+by", re.I)


def blank_label(text, start):
    """המילים שלפני השדה, עד השדה הקודם בלבד. אחרת "ביום __" מקבל את התווית
    של השדה שלפניו ("שנערך ב ביום"), והסוג שנגזר ממנה שגוי."""
    head = text[max(0, start - 30):start]
    last = None
    for m in FIELD_END.finditer(head):
        last = m
    if last:
        head = head[last.end():]
    head = re.split(r"[;,]", head)[-1]
    head = re.sub(r"\s+", " ", head).strip(" :;,–-\t")
    words = head.split(" ")
    return " ".join(words[-3:]).strip()


def type_of_label(label):
    low = label.lower()
    for typ, keys in LABEL_TYPES:
        if any(k.lower() in low for k in keys):
            return typ
    return "טקסט"


def party_names(rows, company):
    """שמות הצדדים מבלוק הצדדים שלפני ההואיל או הסעיף הממוספר הראשון."""
    names, first = [], None
    for r in rows:
        if r["label"] or BODY_START.match(r["text"]):
            break
        t = r["text"].strip()
        if not t or not COMPANY_MARK.search(t):
            continue
        t = PARTY_LEAD.sub("", t)
        t = re.split(r"\s+(?:ח\.?\s?פ|ע\.?\s?מ|ת\.?\s?ז)|,|\(|;|\t", t)[0].strip(" :-–")
        if len(t) < 3 or BLANK_RX.search(t):
            continue
        ours = bool(company) and (norm(company) in norm(t) or norm(t) in norm(company))
        if first is None:
            first = ours if company else None
        names.append((t, ours))
    return names, first


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--family", required=True)
    ap.add_argument("--kind", choices=["template", "agreement"], required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--company", default="")
    a = ap.parse_args()

    ext = os.path.splitext(a.source)[1].lower()
    if ext != ".docx":
        print("הקובץ שמור בפורמט Word ישן או שאינו Word (%s). פתחו אותו ב-Word, "
              "בחרו \"שמירה בשם\" ו-docx, וצרפו שוב." % (ext or "ללא סיומת"))
        sys.exit(2)

    doc = Document(a.source)
    body = doc.element.body
    if body.find(".//" + qn("w:ins")) is not None or body.find(".//" + qn("w:del")) is not None:
        print("המסמך מכיל שינויים במעקב (redline). תבנית אב נבנית ממסמך נקי: "
              "קבלו או דחו את השינויים ב-Word, שמרו, והריצו שוב.")
        sys.exit(2)

    rows = labelled_paragraphs(doc)
    segments = assign_segments(rows)
    names, company_first = party_names(rows, a.company) if a.kind == "agreement" else ([], None)
    counterparty = [n for n, ours in names if not ours]

    variables, by_value, counters = [], {}, {}
    current_clause = None
    in_parties, party_ours = True, False
    unresolved_markers = []
    signing_zone, zone_segment = False, None

    def new_var(typ, label, context, clause, found):
        counters[typ] = counters.get(typ, 0) + 1
        v = {"id": "%s_%d" % (typ, counters[typ]), "type": typ, "label": label,
             "context": context, "clause": clause, "in_clause": bool(r["label"]),
             "segment": r["segment"], "found_value": found, "occurrences": 1}
        variables.append(v)
        return v

    for r in rows:
        if r["label"]:
            current_clause = r["label"]
        text = r["text"]
        if not text.strip():
            continue
        # The party block lists each party's name and then, on following lines, its
        # registration number, address, phone and email. Lines under the company's
        # own name are not variables: they are the company's paper.
        if in_parties and (r["label"] or BODY_START.match(text)):
            in_parties, party_ours = False, False
        if in_parties:
            if re.match(r"^\s*(?:ל\s?ב\s?י\s?ן|and)\b", text, re.I):
                party_ours = False
            for name, ours in names:
                if name in text:
                    party_ours = ours
        spans, taken = [], []

        def free(s, e):
            return all(e <= ts or s >= te for ts, te in taken)

        def add(s, e, v):
            spans.append((s, e, "{{%s}}" % v["id"]))
            taken.append((s, e))

        for m in TAG_RX.finditer(text):
            taken.append((m.start(), m.end()))
            if not any(v["id"] == m.group(1) for v in variables):
                variables.append({"id": m.group(1), "type": "טקסט", "label": m.group(1),
                                  "context": text[max(0, m.start() - 30):m.end() + 20].strip(),
                                  "clause": current_clause, "found_value": None, "occurrences": 1})

        if a.kind == "agreement":
            for name in counterparty:
                for m in re.finditer(re.escape(name), text):
                    if free(m.start(), m.end()):
                        v = by_value.get(("שם_צד", name))
                        if v:
                            v["occurrences"] += 1
                        else:
                            v = by_value[("שם_צד", name)] = new_var(
                                "שם_צד", "שם הצד שכנגד", name, current_clause, name)
                        add(m.start(), m.end(), v)
            for typ, rx in VALUE_PATTERNS:
                for m in rx.finditer(text):
                    s, e = m.span(1)
                    if not free(s, e):
                        continue
                    val = m.group(1)
                    if in_parties and party_ours:
                        continue      # the company's own details stay as they are
                    v = by_value.get((typ, val))
                    if v:
                        v["occurrences"] += 1
                    else:
                        v = by_value[(typ, val)] = new_var(
                            typ, blank_label(text, s) or typ,
                            text[max(0, s - 30):e + 20].strip(), current_clause, val)
                        if typ == "סכום" and r["label"]:
                            v["policy_value"] = True
                    add(s, e, v)

        # A signing line ("תאריך: ...... חתימה: ......") is filled by hand at signing.
        # Turning its blanks into variables would make the draft pre-fill a signature block.
        # After "ולראיה באו הצדדים על החתום" come signature lines that are often bare
        # underscores with no word "חתימה" at all. The zone ends where a new numbering
        # segment (an annex) begins or at an annex heading.
        if re.match(r"^\s*(?:ולראיה|IN\s+WITNESS)", text, re.I):
            signing_zone, zone_segment = True, r["segment"]
        elif signing_zone and (r["segment"] != zone_segment or re.match(r"^\s*(?:נספח|Annex|Schedule|Exhibit)\b", text, re.I)):
            signing_zone = False
        signing = (bool(SIGNING_LINE.search(text)) or signing_zone) and not r["label"]
        for m in MARKERS.finditer(text):
            taken.append((m.start(), m.end()))
            unresolved_markers.append((current_clause, m.group(0)))
        for rx in (BLANK_RX, BRACKET_RX):
            for m in rx.finditer(text):
                if signing or not free(m.start(), m.end()):
                    continue
                label = blank_label(text, m.start())
                v = new_var(type_of_label(label), label or "שדה ריק",
                            text[max(0, m.start() - 30):m.end() + 20].strip(),
                            current_clause, None)
                add(m.start(), m.end(), v)

        if spans:
            replace_spans(r["p"], spans)

    os.makedirs(a.out_dir, exist_ok=True)
    master = os.path.join(a.out_dir, "master.docx")
    doc.save(master)

    warnings = []
    if segments > 1:
        warnings.append("במסמך %d רצפי מספור (כל נספח מתחיל מ-1). הפניה לסעיף נפתרת בתוך הרצף שלה." % segments)
    tops = [x for x in segment_summary(rows)]
    if len(tops) > 1 and tops[0]["top_clauses"] == 1:
        warnings.append("הרצף הראשון מכיל סעיף עליון אחד (\"%s\"), ואחריו המספור מתחיל שוב מ-1. "
                        "כך Word מציג את המקור; כדאי לבדוק אם זו טעות במסמך." % tops[0]["first"])
    if unresolved_markers:
        warnings.append("בתבנית נשארו %d סימוני בדיקה (%s). תבנית אב נשמרת אחרי שנבדקו, "
                        "וסימון שנשאר ייכנס לכל טיוטה שתמולא ממנה."
                        % (len(unresolved_markers), ", ".join(sorted({x[1] for x in unresolved_markers}))))
    body_text = "\n".join(r["text"] for r in rows)
    if "נספח מקורות" in body_text or "נבנתה ללא נייר של החברה" in body_text:
        warnings.append("המסמך כולל נספח מקורות או הודעה שנבנה ללא נייר של החברה. אלה חומר פנימי של "
                        "טיוטת מחקר: לשמירה כתבנית, בנו את הטיוטה מחדש מה-JSON המאושר בלי sources ובלי notice.")
    fields = len(body.findall(".//" + qn("w:ffData"))) + len(body.findall(".//" + qn("w:sdt")))
    if fields:
        warnings.append("%d שדות טופס או בקרי תוכן לא הומרו לתגיות ונשארו כמות שהם." % fields)
    if a.kind == "agreement" and company_first is False:
        warnings.append("החברה אינה מופיעה ראשונה בבלוק הצדדים. ייתכן שזה הנייר של הצד שכנגד, "
                        "ואז הוא אינו שלד מתאים לנייר הבית.")
    if a.kind == "agreement" and a.company and not any(ours for _, ours in names):
        warnings.append("שם החברה לא נמצא בבלוק הצדדים, ולכן לא הוכרע מי הצד שכנגד.")

    skeleton = {
        "family": a.family, "kind": a.kind,
        "source_file": os.path.basename(a.source),
        "source_sha1": hashlib.sha1(open(a.source, "rb").read()).hexdigest(),
        "built_at": datetime.date.today().isoformat(),
        "master": "master.docx",
        "company_listed_first": company_first,
        "segments": segment_summary(rows),
        "body_segment": body_segment(rows),
        "clauses": [{"label": r["label"], "level": r["level"], "segment": r["segment"],
                     "title": r["text"].strip()[:60]} for r in rows if r["label"]],
        "variables": variables,
        "optional_clauses": [],
        "warnings": warnings,
    }
    io.open(os.path.join(a.out_dir, "skeleton.json"), "w", encoding="utf-8").write(
        json.dumps(skeleton, ensure_ascii=False, indent=2))

    print("תבנית אב: %s" % master)
    print("סעיפים ממוספרים: %d · רצפי מספור: %d · משתנים: %d"
          % (len(skeleton["clauses"]), segments, len(variables)))
    for v in variables:
        shown = (" = %s" % v["found_value"]) if v["found_value"] else ""
        if v.get("policy_value"):
            shown += " (ייתכן שזה סף של מדיניות ולא פרט של העסקה)"
        where = ("סעיף %s" if v.get("in_clause") else "אחרי סעיף %s") % v["clause"] if v["clause"] else "פתיח"
        print("  {{%s}}  %s%s  ·  %s  ·  %s" % (v["id"], v["label"], shown, where, v["context"][:60]))
    for w in warnings:
        print("שים לב: " + w)


if __name__ == "__main__":
    main()
