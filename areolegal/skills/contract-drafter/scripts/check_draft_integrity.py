# -*- coding: utf-8 -*-
"""
בודק שלמות פנימית של טיוטה לפני מסירה: מונחים מוגדרים, הפניות פנימיות,
נספחים, מספור, מצייני חוסר, סכומים ותאריכים.

הבדיקה הזאת היא מה שעורך דין עושה בקריאה שנייה, והיא מה שנופל ראשון בלחץ זמן.
הסקריפט אינו מחליף שיקול דעת: הוא מוצא את מה שאפשר למצוא מכנית, ומשאיר את ההכרעה.

הרצה:
  python3 check_draft_integrity.py <draft.docx> [--json out.json] [--strict]

קוד יציאה: 0 אם אין ממצא חוסם, 1 אם יש. --strict הופך גם אזהרה לחוסמת.
"""
import argparse
import io
import json
import os
import re
import sys
from collections import Counter, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_text, docx_paragraphs  # noqa: E402


# ------------------------------------------------------------------ איתור

DEF_RX = [
    re.compile(r'\(\s*להלן\s*:?\s*[""״"]([^""״"]{2,60})[""״"]\s*\)'),
    re.compile(r'[""״"]([^""״"]{2,60})[""״"]\s*[-–—]\s*(?=[א-ת])'),
    re.compile(r'\(\s*hereinafter[:,]?\s+(?:the\s+)?["“]([^"”]{2,60})["”]\s*\)', re.I),
    re.compile(r'\(\s*the\s+["“]([^"”]{2,60})["”]\s*\)', re.I),
]

XREF_RX = re.compile(r"(?:סעיף|סעיפים|ס['׳]|clause|section)\s+(\d+(?:\.\d+)*)", re.I)
ANNEX_REF_RX = re.compile(r"נספח\s+([אבגדהוזחט]['׳]?|\d+)|(?:Exhibit|Schedule|Annex)\s+([A-H]|\d+)")
ANNEX_HEAD_RX = re.compile(
    r"^\s*(?:נספח\s+([אבגדהוזחט]['׳]?|\d+)|(?:Exhibit|Schedule|Annex)\s+([A-H]|\d+))\s*[:\-–]?\s*(.{0,60})$",
    re.I)
CLAUSE_NUM_RX = re.compile(r"^(?:סעיף\s+)?(\d+(?:\.\d+)*)\s*[:\.\)]\s")
PLACEHOLDER_RX = re.compile(
    r"\[להשלים\]|\[TO COMPLETE\]|\[\s*\]|_{3,}|X{3,}|\bTBD\b|\[[^\]\n]{0,40}\?\]|"
    r"\bLorem ipsum\b|<[^>\n]{0,30}>", re.I)
MONEY_RX = re.compile(r"(?:₪|ש\"ח|שקלים|\$|USD|EUR|€)\s*([\d,]+(?:\.\d+)?)|"
                      r"([\d,]{4,}(?:\.\d+)?)\s*(?:₪|ש\"ח|שקלים|dollars?)")
DATE_RX = re.compile(r"\b(\d{1,2})[./](\d{1,2})[./](\d{2,4})\b")
EMDASH_RX = re.compile(r"[—–]")
STALE_RX = re.compile(r"(?:להסכם|הסכם)\s+[א-ת]{2,}\s+מיום\s+\d{1,2}\.\d{1,2}\.\d{4}")


class Report(object):
    def __init__(self):
        self.items = []

    def add(self, level, area, msg, detail=None):
        self.items.append({"level": level, "area": area, "message": msg,
                           "detail": detail or []})

    def blocking(self):
        return [i for i in self.items if i["level"] == "חוסם"]

    def warnings(self):
        return [i for i in self.items if i["level"] == "אזהרה"]


# ------------------------------------------------------------------ בדיקות

def collect_definitions(text):
    """מחזיר את המונחים המוגדרים לפי סדר הופעתם, עם מיקום ההגדרה."""
    defs = OrderedDict()
    for rx in DEF_RX:
        for m in rx.finditer(text):
            term = m.group(1).strip()
            if 2 <= len(term) <= 60 and term not in defs:
                defs[term] = m.start()
    return defs


def check_definitions(text, rep):
    defs = collect_definitions(text)
    if not defs:
        rep.add("אזהרה", "מונחים מוגדרים",
                "לא אותרו מונחים מוגדרים במסמך. אם זה מסמך קצר זה תקין, אחרת יש לבדוק.")
        return defs
    unused, used_before = [], []
    for term, pos in defs.items():
        # ספירת שימושים מחוץ להגדרה עצמה
        hits = [m.start() for m in re.finditer(re.escape(term), text)]
        after = [h for h in hits if h > pos + len(term)]
        before = [h for h in hits if h < pos - 80]
        if not after:
            unused.append(term)
        if before:
            used_before.append(term)
    if unused:
        rep.add("אזהרה", "מונחים מוגדרים",
                "%d מונחים הוגדרו ואינם משמשים בהמשך" % len(unused), unused[:20])
    if used_before:
        rep.add("אזהרה", "מונחים מוגדרים",
                "%d מונחים משמשים לפני שהוגדרו" % len(used_before), used_before[:20])
    # מונח שהוגדר פעמיים בנוסחים שונים
    dup = [t for t, n in Counter(
        [m.group(1).strip() for rx in DEF_RX for m in rx.finditer(text)]).items() if n > 1]
    if dup:
        rep.add("חוסם", "מונחים מוגדרים",
                "מונח מוגדר יותר מפעם אחת. הגדרה כפולה יוצרת סתירה פרשנית", dup[:20])
    return defs


def check_crossrefs(paras, text, rep):
    existing = set()
    for p in paras:
        m = CLAUSE_NUM_RX.match(p.strip())
        if m:
            existing.add(m.group(1))
    if not existing:
        rep.add("אזהרה", "הפניות פנימיות",
                "לא אותר מספור סעיפים בטקסט. אם המספור אוטומטי ב-Word, "
                "יש לאמת את ההפניות ידנית.")
        return
    refs = Counter(m.group(1) for m in XREF_RX.finditer(text))
    dangling = sorted([r for r in refs if r not in existing],
                      key=lambda x: [int(y) for y in x.split(".")])
    if dangling:
        rep.add("חוסם", "הפניות פנימיות",
                "%d הפניות לסעיפים שאינם קיימים במסמך" % len(dangling),
                ["סעיף %s (מוזכר %d פעמים)" % (d, refs[d]) for d in dangling[:20]])
    dups = [n for n, c in Counter(
        [CLAUSE_NUM_RX.match(p.strip()).group(1) for p in paras
         if CLAUSE_NUM_RX.match(p.strip())]).items() if c > 1]
    if dups:
        rep.add("חוסם", "מספור", "מספר סעיף מופיע יותר מפעם אחת", sorted(dups)[:20])
    # רצף המספור הראשי
    tops = sorted({int(e.split(".")[0]) for e in existing})
    gaps = [n for n in range(tops[0], tops[-1] + 1) if n not in tops] if tops else []
    if gaps:
        rep.add("אזהרה", "מספור", "פערים ברצף הסעיפים הראשיים",
                ["חסר סעיף %d" % g for g in gaps[:20]])


def check_annexes(paras, text, rep):
    referenced = set()
    for m in ANNEX_REF_RX.finditer(text):
        referenced.add((m.group(1) or m.group(2) or "").strip("'׳"))
    present = set()
    for p in paras:
        m = ANNEX_HEAD_RX.match(p.strip())
        if m:
            present.add((m.group(1) or m.group(2) or "").strip("'׳"))
    missing = sorted(referenced - present)
    orphan = sorted(present - referenced)
    if missing:
        # נספח עשוי להיות קובץ נפרד, ולכן זו אזהרה ולא ממצא חוסם
        rep.add("אזהרה", "נספחים",
                "נספחים מוזכרים בגוף ההסכם ואין להם כותרת במסמך. "
                "אם הם קבצים נפרדים, יש לוודא שהם מצורפים למשלוח ושהשמות תואמים",
                ["נספח %s" % x for x in missing[:20]])
    if orphan:
        rep.add("אזהרה", "נספחים", "נספחים שמצורפים ואינם מוזכרים בגוף ההסכם",
                ["נספח %s" % x for x in orphan[:20]])


SIGBLOCK_RX = re.compile(r"ולראיה|על\s+החתום|חתימה|חותמת|שם\s*:|תפקיד\s*:|"
                         r"IN\s+WITNESS|signature|title\s*:|name\s*:", re.I)


def check_placeholders(text, rep):
    """שורות חתימה ריקות אינן מצייני חוסר. מסמך חתום ידנית תמיד יכיל קווים
       תחתונים בבלוק החתימה, וסימונם כחוסר מייצר רעש שמכסה על חוסר אמיתי."""
    hits, last = [], -999
    for m in PLACEHOLDER_RX.finditer(text):
        ctx = text[max(0, m.start() - 90):m.start() + 90]
        if m.group(0).startswith("_") and SIGBLOCK_RX.search(ctx):
            continue
        if m.start() - last < 100:      # מיזוג ממצאים סמוכים לממצא אחד
            continue
        last = m.start()
        hits.append(re.sub(r"\s+", " ", text[max(0, m.start() - 50):m.start() + 60]).strip())
    if hits:
        rep.add("חוסם", "מצייני חוסר",
                "%d מצייני חוסר נותרו בטיוטה. מסמך כזה אינו ReadyForExternal" % len(hits),
                hits[:15])


def check_amounts_dates(text, rep):
    nums = [m.group(1) or m.group(2) for m in MONEY_RX.finditer(text)]
    norm = [n.replace(",", "") for n in nums if n]
    dupes = [n for n, c in Counter(norm).items() if c > 1]
    if dupes:
        rep.add("מידע", "סכומים",
                "סכומים החוזרים יותר מפעם אחת. יש לוודא שהחזרה מכוונת ואינה סתירה",
                [d for d in dupes[:12]])
    bad = []
    for m in DATE_RX.finditer(text):
        d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if mo > 12 or d > 31:
            bad.append(m.group(0))
        elif len(y) == 2:
            bad.append(m.group(0) + " (שנה דו ספרתית)")
    if bad:
        rep.add("אזהרה", "תאריכים", "תאריכים בעייתיים או לא חד משמעיים", bad[:15])


def check_style(text, rep, hebrew):
    if hebrew:
        n = len(EMDASH_RX.findall(text))
        if n:
            rep.add("חוסם", "סגנון",
                    "%d מקפים ארוכים במסמך עברי. יש להחליף בפסיק, בנקודה או בנקודתיים" % n)
    stale = [m.group(0) for m in STALE_RX.finditer(text)]
    if stale:
        rep.add("מידע", "שמות תקדים",
                "הפניות להסכמים אחרים בגוף המסמך. יש לוודא שאינן שריד מתבנית",
                list(dict.fromkeys(stale))[:12])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("draft")
    ap.add_argument("--json")
    ap.add_argument("--strict", action="store_true",
                    help="אזהרה נחשבת ממצא חוסם")
    args = ap.parse_args()

    if not os.path.isfile(args.draft):
        print("הקובץ לא נמצא: %s" % args.draft)
        sys.exit(2)
    if args.draft.lower().endswith(".docx"):
        text = docx_text(args.draft, limit=400000)[0]
        paras = docx_paragraphs(args.draft, limit=20000)
    else:
        text = io.open(args.draft, encoding="utf-8", errors="ignore").read()
        paras = text.split("\n")
    if not text.strip():
        print("לא הופק טקסט מהמסמך.")
        sys.exit(2)

    hebrew = len(re.findall(r"[א-ת]", text)) > len(re.findall(r"[A-Za-z]", text))
    rep = Report()
    check_definitions(text, rep)
    check_crossrefs(paras, text, rep)
    check_annexes(paras, text, rep)
    check_placeholders(text, rep)
    check_amounts_dates(text, rep)
    check_style(text, rep, hebrew)

    print("בדיקת שלמות: %s" % os.path.basename(args.draft))
    order = {"חוסם": 0, "אזהרה": 1, "מידע": 2}
    for it in sorted(rep.items, key=lambda x: order.get(x["level"], 3)):
        print("  [%s] %s: %s" % (it["level"], it["area"], it["message"]))
        for d in it["detail"][:8]:
            print("        %s" % d)
    if not rep.items:
        print("  לא נמצאו ממצאים.")
    print("סיכום: %d חוסמים, %d אזהרות" % (len(rep.blocking()), len(rep.warnings())))

    if args.json:
        io.open(args.json, "w", encoding="utf-8").write(json.dumps(
            {"file": os.path.basename(args.draft), "hebrew": hebrew,
             "findings": rep.items,
             "blocking": len(rep.blocking()), "warnings": len(rep.warnings())},
            ensure_ascii=False, indent=2))

    fail = len(rep.blocking()) or (args.strict and len(rep.warnings()))
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
