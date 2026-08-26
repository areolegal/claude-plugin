# -*- coding: utf-8 -*-
"""
לומד את סגנון הנייר של הלקוח מתוך התבניות המאושרות שבמרשם, ומפיק house-style.json.

הרכיב נפגש בכל התקנה עם תיקייה זרה. אסור לו לכתוב לפי הרגלי ניסוח כלליים,
אלא לפי המוסכמות שהחברה הזאת נוהגת בהן בפועל. הסקריפט אינו ממציא כלל:
כל מוסכמה נלמדת בספירה על פני התבניות המאושרות, ונרשמת עם מספר המסמכים שתומכים בה
ועם דוגמה מצוטטת מהמסמך. מוסכמה שאין לה רוב ברור מסומנת כשנויה ונשלחת לאישור המשתמש.

הרצה:
  python3 build_house_style.py --registry <path/template-registry.json> --out <path/house-style.json>
"""
import argparse
import io
import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import (docx_text, docx_paragraphs,  # noqa: E402
                                     docx_num_formats)


# ------------------------------------------------------------------ גלאים

AUTO_FMT = {"decimal": "ספרות", "hebrew1": "אותיות עבריות", "hebrew2": "אותיות עבריות",
            "lowerLetter": "אותיות לטיניות קטנות", "upperLetter": "אותיות לטיניות גדולות",
            "lowerRoman": "ספרות רומיות קטנות", "upperRoman": "ספרות רומיות גדולות",
            "bullet": "תבליט"}


def detect_numbering(paras, path=None):
    """מבנה המספור הנהוג. נבדק על פסקאות, ולא על טקסט משוטח,
       מפני שהמספר יושב בתחילת פסקה. אם המספור אוטומטי ואינו בטקסט,
       נקרא הפורמט מתוך numbering.xml."""
    dec1 = dec2 = dec3 = heb = par = 0
    for p in paras:
        if re.match(r"^\d+\.\d+\.\d+[\.\s]", p):
            dec3 += 1
        elif re.match(r"^\d+\.\d+[\.\s]", p):
            dec2 += 1
        elif re.match(r"^\d+[\.\)]\s", p):
            dec1 += 1
        if re.match(r"^[אבגדהוזחט]['׳]\s", p):
            heb += 1
        elif re.match(r"^\([אבגדהוזחט]\)\s", p):
            par += 1
    if dec1 + dec2 + dec3 + heb + par < 3 and path:
        fmts = docx_num_formats(path)
        labels = [AUTO_FMT.get(f, f) for f, _ in fmts if f != "bullet"]
        if labels:
            uniq = []
            for l in labels:
                if l not in uniq:
                    uniq.append(l)
            return "מספור אוטומטי של Word (%s)" % ", ".join(uniq[:3])
    if dec3 >= 3:
        return "עשרוני תלת רמתי (1, 1.1, 1.1.1)"
    if dec2 >= 3:
        return "עשרוני דו רמתי (1, 1.1)"
    if dec1 >= 3 and (heb + par) >= 3:
        return "עשרוני בסעיפים ראשיים, אותיות עבריות בסעיפי משנה"
    if dec1 >= 3:
        return "עשרוני חד רמתי (1, 2, 3)"
    if heb + par >= 3:
        return "אלפביתי עברי"
    return None


DEF_PATTERNS = [
    ('(להלן: "X")', r'\(להלן:\s*[""״"]'),
    ('(להלן "X")', r'\(להלן\s+[""״"]'),
    ('("X")', r'\(\s*[""״"][^""״"]{2,40}[""״"]\s*\)'),
    ('hereinafter "X"', r'\(hereinafter[:,]?\s+(?:the\s+)?["“]'),
    ('(the "X")', r'\(the\s+["“]'),
]

SIGN_PATTERNS = [
    ("ולראיה באו הצדדים על החתום", r"ולראיה\s+באו\s+הצדדים\s+על\s+החתום"),
    ("ובאו הצדדים על החתום", r"ובאו\s+הצדדים\s+על\s+החתום"),
    ("ולראיה באנו על החתום", r"ולראיה\s+באנו\s+על\s+החתום"),
    ("IN WITNESS WHEREOF", r"IN\s+WITNESS\s+WHEREOF"),
]

PREAMBLE_PATTERNS = [
    ("הואיל וכן הואיל, בסיום: לפיכך הוסכם", r"הואיל"),
    ("WHEREAS", r"WHEREAS"),
]

ANNEX_PATTERNS = [
    ("נספח א', נספח ב'", r"נספח\s+[אבגדה]['׳]"),
    ("נספח 1, נספח 2", r"נספח\s+\d"),
    ("תוספת ראשונה", r"תוספת\s+(?:ראשונה|שנייה|שלישית)"),
    ("Exhibit A / Schedule 1", r"(?:Exhibit\s+[A-D]|Schedule\s+\d)"),
]

LAW_PATTERNS = [
    ("הדין הישראלי", r"דיני\s+מדינת\s+ישראל|הדין\s+הישראלי|חוקי\s+מדינת\s+ישראל"),
    ("Laws of the State of Israel", r"laws\s+of\s+the\s+State\s+of\s+Israel"),
    ("דין זר", r"laws\s+of\s+the\s+State\s+of\s+(?:New\s+York|Delaware|California)|"
              r"laws\s+of\s+England"),
]

FORUM_CITIES = [
    ("בתי המשפט במחוז מרכז", r"מחוז\s+ה?מרכז|\bלוד\b"),
    ("בתי המשפט במחוז תל אביב", r"מחוז\s+תל\s*אביב|בתי\s+המשפט[^.]{0,40}תל\s*אביב"),
    ("בתי המשפט במחוז ירושלים", r"מחוז\s+ירושלים|בתי\s+המשפט[^.]{0,40}ירושלים"),
    ("בתי המשפט במחוז חיפה", r"מחוז\s+חיפה|בתי\s+המשפט[^.]{0,40}חיפה"),
    ("בתי המשפט במחוז דרום", r"מחוז\s+ה?דרום|באר\s*שבע"),
    ("בתי המשפט במחוז צפון", r"מחוז\s+ה?צפון|\bנצרת\b"),
]
FORUM_CONTEXT = r"סמכות\s+(?:שיפוט|השיפוט|מקומית|ייחודית)|סמכות\s+בלעדית|" \
                r"exclusive\s+jurisdiction|venue\b"
ARBITRATION = r"יימסר\s+לבורר|יוכרע\s+בבוררות|הליך\s+בוררות|\barbitration\b"


def detect_forum(t):
    """סמכות שיפוט נקבעת רק מתוך סעיף הסמכות. חיפוש שם עיר בכל המסמך
       שוגה, מפני שכתובת צד בתל אביב אינה קביעת סמכות שיפוט."""
    arb = re.search(ARBITRATION, t, re.I)
    first = None
    for m in re.finditer(FORUM_CONTEXT, t, re.I):
        window = re.sub(r"\s+", " ", t[max(0, m.start() - 120):m.start() + 420]).strip()
        for label, rx in FORUM_CITIES:
            if re.search(rx, window):
                if arb:
                    return label + ", בכפוף לסעיף בוררות", window
                return label, window
        if first is None:
            first = window
    if arb:
        return "בוררות", re.sub(r"\s+", " ", t[max(0, arb.start() - 60):arb.start() + 200]).strip()
    if first:
        return "נקבעה סמכות שיפוט בלי ציון מקום מזוהה", first
    return None, None

PARTY_LABELS = ["החברה", "הספק", "הלקוח", "נותן השירותים", "מקבל השירותים",
                "המזמין", "הקבלן", "המפיץ", "היצרן", "המשכיר", "השוכר",
                "בעל הרישיון", "מעניק הרישיון", "הצד הראשון", "הצד השני"]


def find_first(t, patterns, window=140):
    """מחזיר (תווית, ציטוט קצר) עבור התבנית הראשונה שנמצאה."""
    for label, rx in patterns:
        m = re.search(rx, t, re.I)
        if m:
            start = max(0, m.start() - 30)
            quote = re.sub(r"\s+", " ", t[start:m.start() + window]).strip()
            return label, quote
    return None, None


def detect_date_format(t):
    if re.search(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b", t):
        return "יום.חודש.שנה"
    if re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", t):
        return "יום/חודש/שנה"
    if re.search(r"ביום\s+\d{1,2}\s+ב?[א-ת]+\s+\d{4}", t):
        return "מילולי (ביום 3 במרץ 2026)"
    return None


def detect_language(t):
    heb = len(re.findall(r"[א-ת]", t))
    lat = len(re.findall(r"[A-Za-z]", t))
    if heb > lat * 2:
        return "עברית"
    if lat > heb * 2:
        return "אנגלית"
    return "דו לשוני"


# ------------------------------------------------------------------ צבירה

class Convention(object):
    """אוסף עדויות למוסכמה אחת ומכריע לפי רוב, עם שקיפות מלאה."""

    def __init__(self, name, question):
        self.name = name
        self.question = question
        self.votes = Counter()
        self.evidence = {}

    def add(self, value, source, quote=None):
        if not value:
            return
        self.votes[value] += 1
        self.evidence.setdefault(value, {"source": source, "quote": quote})

    def resolve(self, total):
        if not self.votes:
            return {"name": self.name, "question": self.question, "value": None,
                    "status": "לא נלמדה", "note": "לא אותרה מוסכמה בתבניות המאושרות, יש לשאול את המשתמש"}
        ranked = self.votes.most_common()
        top_val, top_n = ranked[0]
        second_n = ranked[1][1] if len(ranked) > 1 else 0
        if top_n == second_n:
            status = "שנויה"
        elif top_n >= max(2, (total + 1) // 2):
            status = "מבוססת"
        else:
            status = "טעונה אישור"
        ev = self.evidence.get(top_val, {})
        return {
            "name": self.name,
            "question": self.question,
            "value": top_val,
            "status": status,
            "support": "%d מתוך %d תבניות מאושרות" % (top_n, total),
            "alternatives": [{"value": v, "count": n} for v, n in ranked[1:4]],
            "source_file": ev.get("source"),
            "example": ev.get("quote"),
        }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    reg = json.load(io.open(args.registry, encoding="utf-8"))
    docs = [d for d in reg.get("documents", []) if d.get("approved_current")]
    if not docs:
        print("אין תבניות מאושרות במרשם. יש להריץ תחילה את build_template_registry.py "
              "ולאשר תבניות מול המשתמש.")
        sys.exit(2)

    C = {
        "numbering": Convention("מבנה המספור", "כיצד ממוספרים הסעיפים וסעיפי המשנה"),
        "defined": Convention("סימון מונחים מוגדרים", "כיצד מוגדר מונח בפעם הראשונה"),
        "preamble": Convention("מבוא ההסכם", "האם ההסכם נפתח בהואילים"),
        "signature": Convention("נוסח סגירת החתימה", "מהי שורת החתימה הנהוגה"),
        "annex": Convention("שמות הנספחים", "כיצד ממוספרים הנספחים"),
        "law": Convention("הדין החל", "מהו הדין החל שבתבניות"),
        "forum": Convention("סמכות השיפוט", "היכן נקבעת סמכות השיפוט"),
        "date": Convention("מבנה התאריך", "כיצד נכתבים תאריכים בגוף ההסכם"),
        "language": Convention("שפת ההסכם", "באיזו שפה נערכות התבניות"),
    }
    party_votes = Counter()
    scanned = []

    for d in docs:
        path = os.path.join(d.get("folder", ""), d["file"])
        try:
            if path.lower().endswith(".docx"):
                t = docx_text(path)[0]  # docx_text מחזיר (טקסט, עקוב אחר שינויים, הערות)
            else:
                t = io.open(path, encoding="utf-8", errors="ignore").read()
        except Exception as e:
            print("  דילוג על %s: %s" % (d["file"], e))
            continue
        if not t or len(t) < 500:
            continue
        scanned.append(d["file"])
        src = d["file"]

        paras = docx_paragraphs(path) if path.lower().endswith(".docx") else t.split("\n")
        C["numbering"].add(detect_numbering(paras, path), src)
        for key, pats in (("defined", DEF_PATTERNS), ("preamble", PREAMBLE_PATTERNS),
                          ("signature", SIGN_PATTERNS), ("annex", ANNEX_PATTERNS),
                          ("law", LAW_PATTERNS)):
            label, quote = find_first(t, pats)
            C[key].add(label, src, quote)
        flabel, fquote = detect_forum(t)
        C["forum"].add(flabel, src, fquote)
        C["date"].add(detect_date_format(t), src)
        C["language"].add(detect_language(t), src)

        for lbl in PARTY_LABELS:
            if re.search(r'[""״"]%s[""״"]' % re.escape(lbl), t) or \
               len(re.findall(r"\b%s\b" % re.escape(lbl), t)) >= 5:
                party_votes[lbl] += 1

    total = len(scanned)
    out = {
        "generated_at": __import__("datetime").date.today().strftime("%d.%m.%Y"),
        "source": "נלמד מתוך התבניות המאושרות של הלקוח בלבד",
        "templates_scanned": total,
        "template_files": scanned,
        "conventions": [C[k].resolve(total) for k in
                        ["language", "numbering", "defined", "preamble", "annex",
                         "signature", "law", "forum", "date"]],
        "party_labels": [{"label": l, "templates": n} for l, n in party_votes.most_common(8)],
        "confirmation_required": [],
        "disclaimer": ("המוסכמות נלמדו בספירה אוטומטית ומחייבות אישור המשתמש לפני שהן משמשות "
                       "לניסוח. מוסכמה שסטטוסה שנויה או טעונה אישור לא תיושם בלי אישור מפורש."),
    }
    out["confirmation_required"] = [c["name"] for c in out["conventions"]
                                    if c["status"] in ("שנויה", "טעונה אישור", "לא נלמדה")]

    d = os.path.dirname(os.path.abspath(args.out))
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(args.out, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=2))

    print("נלמדו %d תבניות מאושרות" % total)
    for c in out["conventions"]:
        print("  %-24s %-46s %s" % (c["name"], (c["value"] or "לא נלמדה")[:46], c["status"]))
    if out["party_labels"]:
        print("  כינויי צדדים נפוצים: " +
              ", ".join(p["label"] for p in out["party_labels"][:5]))
    if out["confirmation_required"]:
        print("טעון אישור המשתמש: " + ", ".join(out["confirmation_required"]))


if __name__ == "__main__":
    main()
