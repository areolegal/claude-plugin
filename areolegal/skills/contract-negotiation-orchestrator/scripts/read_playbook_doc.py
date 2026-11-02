#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""קורא פלייבוק של הלקוח ממסמך Word, PDF או Excel, בלי לכתוב דבר לתיקיית הלקוח.

מסמך של הלקוח משמש כמו שהוא (`n3-decisions.md`, "מקור העמדות", "יש פלייבוק:
שימוש"; הערות הנושא ונותן, שינוי 45). הקורא מחזיר את מה שבמסמך, בלי להשלים
ובלי לפרש: הנושאים, המסלולים ותנאיהם, סימני האדום, הנוסחים החלופיים, הסגמנטים,
וכללי ההפעלה שהמסמך קובע לעצמו (פרק "הוראות הפעלה"). שדה שאין לו מקור במסמך
נשאר ריק, וההחלה ממלאת אותו לפי `n3b-matrix.md`, ולא הקורא.

איך הוא קורא:
* **טבלה** שבשורת הכותרת שלה עמודות של מסלולים (ירוק, צהוב, אדום; Green,
  Yellow, Red; מועדף, נסיגה, קו אדום; Preferred, Fallback, Walk-away; Standard,
  Acceptable, Unacceptable), לפי מילה שלמה: כל שורה היא נושא.
* **כותרות**: כל כותרת (סגנון כותרת, שורה ממוספרת קצרה, או שורה מודגשת קצרה)
  פותחת נושא, והשורות שאחריה משויכות למסלול לפי התווית שבתחילתן.
* **Excel**: כל גיליון עם שורת כותרת כזו; נדרש openpyxl.
* **PDF**: שכבת הטקסט, שורה אחר שורה; PDF סרוק אינו נקרא, ונאמר.

    python "AREO_RT/skills/contract-negotiation-orchestrator/scripts/read_playbook_doc.py" "<המסמך>" [--out <תיקייה זמנית>/playbook-read.json]

קוד יציאה: **0** נקרא, **3** לא נמצא בו אף נושא (המסמך אינו פלייבוק, או שאינו
קריא), **2** קלט חסר, או Word פגום, DOC, מוצפן או Strict (הודעה דו-לשונית), **1** `--out` בתיקיית הלקוח, על
המסמך עצמו או על מסמך קיים.
"""
import argparse
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from common.cli import OutputRefused, guard_out, load_docx_or_explain  # noqa: E402

# ביקורת כלליות, ממצא 5: אותן תוויות לכותרת של עמודה ולתווית בתחילת שורה, ותמיד כמילה שלמה ("red" אינו
# נמצא בתוך "Preferred", "acceptable" אינו נמצא בתוך "Unacceptable"). אדום נבדק ראשון, כי "לא מקובל" ו-"Not
# acceptable" מכילים מילה של צהוב.
TRACK_WORDS = {
    "red": r"מסלול אדום|קו(?:ים)? אדום|קווים אדומים|אדום|לא מקובל(?:ת)?|לא מתקבל|"
           r"red[\s\-]lines?|red|unacceptable|not acceptable|walk[\s\-]?away|deal[\s\-]?breakers?|no[\s\-]?go",
    "yellow": r"מסלול צהוב|צהוב|עמדת נסיגה|נסיגה|ויתור מותר|פשרה|"
              r"yellow|fall[\s\-]?back|acceptable|compromise",
    "green": r"מסלול ירוק|ירוק|עמדה מועדפת|מועדפ(?:ת|ים|ות)|מועדף|רגיל(?:ה)?|ברירת מחדל|העמדה שלנו|"
             r"green|preferred(?: position)?|standard(?: position)?|ideal",
}
_LB, _LA = r"(?<![^\W\d_])", r"(?![^\W\d_])"   # לא אות לפני המונח ולא אות אחריו
# "Red flags:" היא תווית של סימני אדום (FIELD_LABELS), ולא של המסלול האדום
TRACK_LABELS = {k: r"^(?:ה)?(?:%s)%s(?!\s+flags)" % (rx, _LA) for k, rx in TRACK_WORDS.items()}
FIELD_LABELS = {
    "red_flags": r"^(?:סימני אדום|סימני זיהוי|סימנים|red flags|flags|watch for)\b",
    "alternatives": r"^(?:נוסח חלופי|נוסח מוצע|נוסח|alternative wording|proposed wording|wording|clause)\b",
    "segment": r"^(?:סגמנט|פלח|segment)\b",
    "notes": r"^(?:הערה|הערות|הסבר|נימוק|note|notes|rationale)\b",
}
OPERATING = re.compile(r"הוראות הפעלה|כללי הפעלה|אופן השימוש|operating (?:rules|instructions)|how to use", re.I)
HEADER_TRACKS = {k: re.compile(_LB + r"(?:[וה])?(?:%s)" % rx + _LA, re.I) for k, rx in TRACK_WORDS.items()}
HEADER_TOPIC = re.compile(_LB + r"(?:ה)?(?:נושא|סעיף|topic|clause|issue|term|provision)s?" + _LA, re.I)
HEADER_FLAGS = re.compile(r"סימני|flags", re.I)


def strip_label(text, rx):
    return re.sub(rx + r"\s*[:\-.]?\s*", "", text, count=1, flags=re.I).strip()


def header_track(h):
    """המסלול של כותרת עמודה, או None. אדום קודם, ואחריו צהוב וירוק (HEADER_TRACKS לפי הסדר)."""
    if HEADER_FLAGS.search(h):
        return None
    return next((k for k, rx in HEADER_TRACKS.items() if rx.search(h)), None)


def topic_from_table(rows):
    """rows: רשימת רשימות. מחזיר נושאים כשבשורת הכותרת יש עמודות של מסלולים."""
    # שורת הכותרת היא הראשונה, מבין עשר השורות הראשונות, שיש בה שתי עמודות של מסלולים לפחות: בגיליון Excel
    # יש לעיתים שורת כותרת של המסמך מעל הטבלה
    for n, row in enumerate((rows or [])[:10]):
        head = [str(c or "") for c in row]
        tracks = [header_track(h) for h in head]
        cols = {k: next((i for i, t in enumerate(tracks) if t == k), None) for k in ("green", "yellow", "red")}
        if sum(v is not None for v in cols.values()) >= 2:
            rows = rows[n:]
            break
    else:
        return []
    tcol = next((i for i, h in enumerate(head) if HEADER_TOPIC.search(h) and tracks[i] is None), 0)
    fcol = next((i for i, h in enumerate(head) if HEADER_FLAGS.search(h)), None)
    out = []
    for r in rows[1:]:
        r = [str(c or "").strip() for c in r]
        if not any(r) or tcol >= len(r) or not r[tcol]:
            continue
        t = {"topic": r[tcol], "red_flags": [], "alternatives": [], "notes": []}
        for k, i in cols.items():
            t[k] = r[i] if i is not None and i < len(r) else ""
        if fcol is not None and fcol < len(r) and r[fcol]:
            t["red_flags"] = [x.strip() for x in re.split(r"[;\n•]", r[fcol]) if x.strip()]
        out.append(t)
    return out


def topics_from_lines(lines):
    """lines: [(text, is_heading)]. כותרת פותחת נושא; שורה עם תווית משויכת למסלול או לשדה."""
    topics, segments, operating, cur, in_ops = [], [], [], None, False
    for text, heading in lines:
        text = text.strip()
        if not text:
            continue
        if heading:
            in_ops = bool(OPERATING.search(text))
            if not in_ops:
                cur = {"topic": re.sub(r"^\d+(?:\.\d+)*[.)]?\s*", "", text), "green": "", "yellow": "", "red": "",
                       "red_flags": [], "alternatives": [], "notes": []}
                topics.append(cur)
            continue
        if in_ops:
            operating.append(text)
            continue
        if cur is None:
            continue
        for k, rx in TRACK_LABELS.items():
            if re.search(rx, text, re.I):
                cur[k] = (cur[k] + " " + strip_label(text, rx)).strip()
                break
        else:
            for k, rx in FIELD_LABELS.items():
                if re.search(rx, text, re.I):
                    val = strip_label(text, rx)
                    if k == "segment":
                        segments.append({"topic": cur["topic"], "segment": val})
                    elif k == "red_flags":
                        cur["red_flags"] += [x.strip() for x in re.split(r"[;•]", val) if x.strip()]
                    else:
                        cur[k].append(val)
                    break
            else:
                cur["notes"].append(text)
    topics = [t for t in topics if t["green"] or t["yellow"] or t["red"] or t["red_flags"]]
    return topics, segments, operating


def read_docx(path, d=None):
    if d is None:
        import docx
        d = docx.Document(path)
    topics = []
    for tb in d.tables:
        topics += topic_from_table([[c.text for c in row.cells] for row in tb.rows])
    lines = []
    for p in d.paragraphs:
        t = p.text.strip()
        style = (p.style.name or "").lower() if p.style is not None else ""
        bold = bool(p.runs) and all(r.bold for r in p.runs if r.text.strip())
        heading = style.startswith(("heading", "כותרת", "title")) or \
            (len(t) <= 70 and (bold or re.match(r"^\d+(?:\.\d+)?[.)]\s+\S", t)) and not re.search(r"[.:]$", t)
             and not any(re.search(rx, t, re.I) for rx in list(TRACK_LABELS.values()) + list(FIELD_LABELS.values())))
        lines.append((t, heading))
    more, segments, operating = topics_from_lines(lines)
    return topics + more, segments, operating


def read_pdf(path):
    from risk.page_text import PdfTextUnavailable, pdf_text
    with open(path, "rb") as fh:
        raw = fh.read()
    try:
        text = pdf_text(raw)
    except PdfTextUnavailable as exc:
        raise ValueError("ה-PDF אינו נקרא (%s): בקשו מהלקוח עותק Word" % exc)
    lines = []
    for l in text.splitlines():
        t = l.strip()
        heading = bool(re.match(r"^\d+(?:\.\d+)?[.)]?\s+\S", t)) and len(t) <= 70 and not re.search(r"[.:]$", t)
        lines.append((t, heading))
    return topics_from_lines(lines)


def read_xlsx(path):
    try:
        import openpyxl
    except ImportError:
        raise ValueError("לקריאת Excel נדרש openpyxl (pip install openpyxl)")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    topics, operating = [], []
    for ws in wb.worksheets:
        rows = [list(r) for r in ws.iter_rows(values_only=True)]
        found = topic_from_table(rows)
        if found:
            topics += found
        elif OPERATING.search(ws.title or ""):
            operating += [" ".join(str(c) for c in r if c) for r in rows if any(r)]
    return topics, [], operating


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("file")
    ap.add_argument("--out", help="קובץ JSON בתיקייה זמנית; לעולם לא בתיקיית הלקוח")
    a = ap.parse_args(argv)
    if not os.path.exists(a.file):
        print("המסמך אינו קיים: %s" % a.file)
        return 2
    if a.out and os.path.commonpath([os.path.realpath(a.out), os.path.realpath(os.path.dirname(a.file))]) == \
            os.path.realpath(os.path.dirname(a.file)):
        print("--out בתיקיית הלקוח (%s). הקורא אינו כותב לשם; בחרו תיקייה זמנית." % os.path.dirname(a.file))
        return 1
    if a.out:
        # גם מחוץ לתיקייה של המסמך: לא על המסמך עצמו, לא על מסמך קיים ולא בתיקיית מקור של הלקוח
        try:
            guard_out(a.out, inputs=[a.file])
        except OutputRefused as exc:
            print("סירוב: %s" % exc)
            return 1
    ext = os.path.splitext(a.file)[1].lower()
    doc = None
    if ext in (".docx", ".doc", ".docm"):
        # Word פגום, DOC, מוצפן או Strict: הודעה דו-לשונית וקוד 2, ולא traceback של python-docx
        doc, msg, code = load_docx_or_explain(a.file)
        if doc is None:
            print(msg)
            return code
    try:
        if ext in (".docx", ".doc", ".docm"):
            topics, segments, operating = read_docx(a.file, doc)
        elif ext == ".pdf":
            topics, segments, operating = read_pdf(a.file)
        elif ext in (".xlsx", ".xlsm"):
            topics, segments, operating = read_xlsx(a.file)
        else:
            print("פורמט שאינו נקרא: %s. Word, PDF או Excel." % ext)
            return 2
    except ValueError as exc:
        print(str(exc))
        return 3
    out = {"source": os.path.basename(a.file), "format": ext[1:], "topics": topics, "segments": segments,
           "operating_rules": operating}
    if a.out:
        with io.open(a.out, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False, indent=1))
    if not topics:
        print("לא נמצא במסמך אף נושא עם מסלולים. ייתכן שאינו פלייבוק, או שהוא מסמך רקע (n1b-learning.md, \"מסמך רקע אינו מועמד\").")
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
