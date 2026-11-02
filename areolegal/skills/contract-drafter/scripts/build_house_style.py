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
                                     docx_num_formats, guard_out)

try:                                   # פלט עברי במסוף של Windows
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass


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

# הדין החל: זיהוי כללי של "governed by (and construed in accordance with) the laws of X" ושל "דיני X" או
# "דיני מדינת X" בהקשר של סעיף דין, לכל מדינה. התווית היא "דיני X", בשם כפי שהוא בנייר; השמות שבטבלה
# מאוחדים לשם עברי אחד, כדי שתבנית עברית ותבנית אנגלית של אותו דין ייספרו יחד. אין דין ברירת מחדל.
EN_NAME = r"([A-Z](?:[\w'\-]|\.(?=\w))*(?:\s+(?:[A-Z](?:[\w'\-]|\.(?=\w))*|of|and|the))*)"
EN_STATE_PREFIX = r"(?:the\s+)?(?:(?i:State|Commonwealth|Province|Republic|Federal\s+Republic|Kingdom|" \
                  r"Grand\s+Duchy|Emirate|Canton)\s+of\s+(?:the\s+)?)?"
LAW_EN = [
    re.compile(r"(?i:governed\s+by|construed|interpreted|enforced|governing\s+law)[^.;]{0,90}?"
               r"(?i:laws?)\s+(?i:of)\s+" + EN_STATE_PREFIX + EN_NAME),
    re.compile(r"(?i:laws?)\s+(?i:of)\s+" + EN_STATE_PREFIX + EN_NAME +
               r"(?=[^.;]{0,60}(?i:shall|will)\s+govern)"),
]
# צורת התואר: "governed by English law", "subject to German law", "New York law shall govern"
EN_ADJ = {"English and Welsh": "אנגליה ווילס", "English": "אנגליה", "Welsh": "אנגליה ווילס", "Scottish": "סקוטלנד",
          "Scots": "סקוטלנד", "Northern Irish": "צפון אירלנד", "British": "הממלכה המאוחדת", "German": "גרמניה",
          "French": "צרפת", "Swiss": "שווייץ", "Dutch": "הולנד", "Irish": "אירלנד", "Cypriot": "קפריסין",
          "Israeli": "ישראל", "New York": "ניו יורק", "Delaware": "דלאוור", "Californian": "קליפורניה",
          "California": "קליפורניה", "Texan": "טקסס", "Texas": "טקסס", "New Jersey": "ניו ג'רזי",
          "Massachusetts": "מסצ'וסטס", "Florida": "פלורידה", "Illinois": "אילינוי", "Singaporean": "סינגפור",
          "Singapore": "סינגפור", "Hong Kong": "הונג קונג", "Italian": "איטליה", "Spanish": "ספרד",
          "Portuguese": "פורטוגל", "Belgian": "בלגיה", "Luxembourg": "לוקסמבורג", "Austrian": "אוסטריה",
          "Swedish": "שוודיה", "Danish": "דנמרק", "Norwegian": "נורווגיה", "Finnish": "פינלנד", "Polish": "פולין",
          "Czech": "צ'כיה", "Greek": "יוון", "Maltese": "מלטה", "Japanese": "יפן", "Chinese": "סין", "Indian": "הודו",
          "Canadian": "קנדה", "Ontario": "אונטריו", "Australian": "אוסטרליה", "New Zealand": "ניו זילנד",
          "Brazilian": "ברזיל", "South African": "דרום אפריקה", "Korean": "דרום קוריאה"}
_EN_ADJ_ALT = "|".join(re.escape(k) for k in sorted(EN_ADJ, key=len, reverse=True))
LAW_EN_ADJ = [
    re.compile(r"(?i:governed\s+by|construed|interpreted|enforced|governing\s+law|subject\s+to)[^.;]{0,60}?"
               r"\b(" + _EN_ADJ_ALT + r")\s+(?i:laws?)\b"),
    re.compile(r"\b(" + _EN_ADJ_ALT + r")\s+(?i:laws?)(?=[^.;]{0,40}(?i:shall|will)\s+(?i:govern|apply))"),
]
LAW_HE_CONTEXT = r"הדין\s+החל|יחולו|יחול\s|יפורש|יפורשו|כפוף\s+ל|בכפוף\s+ל|ייקבע\s+על\s+פי|יוכרע\s+לפי|" \
                 r"דין\s+חל|הדין\s+השולט"
LAW_HE = re.compile(r"(?:^|[\s(])[ול]?(?:דיני|חוקי)\s+(מדינת\s+)?([א-ת][א-ת'׳\"״\-]+)(?:\s+([א-ת][א-ת'׳\-]+))?")
LAW_HE_ADJ = re.compile(r"(?:^|[\s(])[ולב]?ה?(?:דין|חוק|משפט)\s+ה([א-ת]{3,}י)(?![א-ת])")
HE_MULTI = {"ניו": ("יורק", "ג'רזי", "ג׳רזי", "זילנד"), "הונג": ("קונג",), "הממלכה": ("המאוחדת",),
            "ארצות": ("הברית",), "דרום": ("אפריקה", "קוריאה"), "איחוד": ("האמירויות",)}
# מילה שבאה אחרי "דיני" ואינה שם של מקום: תחום משפט, לא דין של מדינה
HE_NOT_PLACE = ("הגנת", "מס", "מיסים", "עבודה", "חוזים", "נזיקין", "קניין", "ביטוח", "תחרות", "חברות",
                "ניירות", "פרטיות", "צרכנות", "בוררות", "ראיות", "הסכם", "ההסכם", "הצדדים", "אחרים", "כלשהם")
HE_ADJ = {"ישראלי": "ישראל", "אנגלי": "אנגליה", "סקוטי": "סקוטלנד", "בריטי": "הממלכה המאוחדת",
          "גרמני": "גרמניה", "צרפתי": "צרפת", "הולנדי": "הולנד", "קנדי": "קנדה", "אוסטרלי": "אוסטרליה",
          "בלגי": "בלגיה", "אוסטרי": "אוסטריה", "פולני": "פולין", "פורטוגלי": "פורטוגל", "הודי": "הודו",
          "שווייצרי": "שווייץ", "אירי": "אירלנד", "קפריסאי": "קפריסין", "אמריקאי": "ארצות הברית",
          "אמריקני": "ארצות הברית", "סינגפורי": "סינגפור", "יפני": "יפן", "איטלקי": "איטליה", "ספרדי": "ספרד"}
NAME_HE = {"israel": "ישראל", "england": "אנגליה", "england and wales": "אנגליה ווילס",
           "the united kingdom": "הממלכה המאוחדת", "united kingdom": "הממלכה המאוחדת", "new york": "ניו יורק",
           "delaware": "דלאוור", "california": "קליפורניה", "germany": "גרמניה", "france": "צרפת",
           "the netherlands": "הולנד", "netherlands": "הולנד", "switzerland": "שווייץ", "singapore": "סינגפור",
           "ireland": "אירלנד", "cyprus": "קפריסין", "japan": "יפן", "italy": "איטליה", "spain": "ספרד",
           "luxembourg": "לוקסמבורג", "the united states": "ארצות הברית", "united states": "ארצות הברית"}


def _en_name(raw):
    """שם התחום כפי שנתפס בביטוי האנגלי, בלי מילות קישור בסופו."""
    name = re.sub(r"(?:[\s,]+(?:and|of|the))+$", "", raw.strip(" ,.")).strip(" ,.")
    return NAME_HE.get(name.lower(), name)


def detect_law(t):
    """(תווית, ציטוט) של הדין החל, או (None, None). אנגלית: governed by / construed ... the laws of X;
       עברית: "דיני X" או "דיני מדינת X" או "הדין ה-X-י" בחלון של סעיף דין."""
    for rx in LAW_EN:
        for m in rx.finditer(t):
            name = _en_name(m.group(1))
            if name:
                return "דיני %s" % name, re.sub(r"\s+", " ", t[max(0, m.start() - 30):m.end() + 60]).strip()
    for rx in LAW_EN_ADJ:
        for m in rx.finditer(t):
            key = next((k for k in EN_ADJ if k.lower() == m.group(1).lower()), None)
            if key:
                return "דיני %s" % EN_ADJ[key], re.sub(r"\s+", " ", t[max(0, m.start() - 30):m.end() + 60]).strip()
    for c in re.finditer(LAW_HE_CONTEXT, t):
        a, b = max(0, c.start() - 90), c.start() + 220
        window = t[a:b]
        for m in LAW_HE.finditer(window):
            state, w1, w2 = m.group(1), m.group(2), m.group(3)
            if not state and (w1 in HE_NOT_PLACE or w1.startswith("ה") and w1 not in ("הולנד", "הודו", "הונג")):
                continue
            name = w1 + (" " + w2 if w2 and w2 in HE_MULTI.get(w1, ()) else "")
            return "דיני %s" % name, re.sub(r"\s+", " ", window).strip()
        # רק תואר של מקום מהטבלה: "הדין הכללי" או "המשפט המסחרי" אינם דין של מדינה
        for m in LAW_HE_ADJ.finditer(window):
            if m.group(1) in HE_ADJ:
                return "דיני %s" % HE_ADJ[m.group(1)], re.sub(r"\s+", " ", window).strip()
    return None, None

# אין רשימת בתי משפט או מחוזות בקוד: הפורום נקרא מסעיף הסמכות עצמו (FORUM_EN, FORUM_HE)
FORUM_CITIES = []
FORUM_CONTEXT = r"סמכות\s+(?:שיפוט|השיפוט|מקומית|ייחודית)|סמכות\s+בלעדית|" \
                r"exclusive\s+jurisdiction|venue\b|jurisdiction\s+of\s+the\s+courts|submit\s+to\s+the|courts\s+of\b"
# פורום בכל מקום, בעברית ובאנגלית: "courts of X", "exclusive jurisdiction of the courts of X", "בתי המשפט ב-X"
FORUM_EN = re.compile(r"(?i:courts?)\s+(?i:of|in|located\s+in|sitting\s+in)\s+" + EN_STATE_PREFIX +
                      r"(?:(?i:the\s+)?(?i:City|County|Borough)\s+of\s+)?" +
                      r"([A-Z](?:[\w'\-]|\.(?=\w))*(?:(?:\s+|,\s*)(?:[A-Z](?:[\w'\-]|\.(?=\w))*|of|and|the))*)")
FORUM_HE = re.compile(r"בתי\s+ה?משפט\s+(?:ה?מוסמכים\s+)?ב(?:מדינת\s+|עיר\s+)?([א-ת][א-ת'׳\"״\-]+)"
                      r"(?:\s+([א-ת][א-ת'׳\-]+))?")
ARBITRATION = r"יימסר\s+לבורר|יוכרע\s+בבוררות|הליך\s+בוררות|\barbitration\b"


def detect_forum(t):
    """סמכות שיפוט נקבעת רק מתוך סעיף הסמכות. חיפוש שם עיר בכל המסמך
       שוגה, מפני שכתובת צד בתל אביב אינה קביעת סמכות שיפוט."""
    arb = re.search(ARBITRATION, t, re.I)
    first = None
    for m in re.finditer(FORUM_CONTEXT, t, re.I):
        window = re.sub(r"\s+", " ", t[max(0, m.start() - 120):m.start() + 420]).strip()
        label = next((lb for lb, rx in FORUM_CITIES if re.search(rx, window)), None)
        if not label:
            mf = FORUM_EN.search(window)
            if mf and _en_name(mf.group(1)):
                nm = _en_name(mf.group(1))
                label = ("בתי המשפט ב" if re.match(r"[א-ת]", nm) else "בתי המשפט ב-") + nm
            else:
                mh = FORUM_HE.search(window)
                md = re.search(r"במחוז\s+([א-ת'׳\-]+)(?:\s+([א-ת'׳\-]+))?", window)
                if mh and mh.group(1) == "מחוז" and md:
                    w2 = md.group(2) if md.group(2) and md.group(2) not in ("בלבד", "או", "תהא", "הנתונה", "ושם")                         and not md.group(2).startswith("ו") else ""
                    label = "בתי המשפט במחוז %s" % (md.group(1) + (" " + w2 if w2 else ""))
                elif mh and not mh.group(1).startswith("מחוז"):
                    w1, w2 = mh.group(1), mh.group(2)
                    label = "בתי המשפט ב%s" % (w1 + (" " + w2 if w2 and w2 in HE_MULTI.get(w1, ()) else ""))
        if label:
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

# כינויי הצדדים: אין אוצר תפקידים. כינוי נספר כשהוא מוגדר במירכאות בפתיח ("<תפקיד>"), כלשון המסמך. כינויים
# כלליים בלבד נספרים גם בלי מירכאות (PARTY_COUNTED), כי מילה רגילה בגוף ההסכם אינה כינוי
_GENERIC_LABELS = ["החברה", "הצד הראשון", "הצד השני", "Company", "Party A", "Party B"]
PARTY_COUNTED = {"החברה", "הצד הראשון", "הצד השני"}
_EXTRA_LABELS = []


def _label_form(w):
    w = w.strip()
    if re.match(r"[A-Za-z]", w):
        w = re.sub(r"^the\s+", "", w, flags=re.I)
        return " ".join(x[:1].upper() + x[1:] for x in w.split())
    return w


PARTY_LABELS = []
for _w in _GENERIC_LABELS + _EXTRA_LABELS:
    _w = _label_form(_w)
    if _w and _w not in PARTY_LABELS:
        PARTY_LABELS.append(_w)


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
    guard_out(args.out, [args.registry])

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
                          ("signature", SIGN_PATTERNS), ("annex", ANNEX_PATTERNS)):
            label, quote = find_first(t, pats)
            C[key].add(label, src, quote)
        llabel, lquote = detect_law(t)
        C["law"].add(llabel, src, lquote)
        flabel, fquote = detect_forum(t)
        C["forum"].add(flabel, src, fquote)
        C["date"].add(detect_date_format(t), src)
        C["language"].add(detect_language(t), src)

        for lbl in PARTY_LABELS:
            if re.search(r'["״“”]%s["״“”]' % re.escape(lbl), t) or \
               (lbl in PARTY_COUNTED and len(re.findall(r"\b%s\b" % re.escape(lbl), t)) >= 5):
                party_votes[lbl] += 1

    total = len(scanned)
    out = {
        "generated_at": __import__("datetime").date.today().isoformat(),   # ISO ב-JSON (כלל 3.6)
        "source": "נלמד מתוך התבניות המאושרות של הלקוח בלבד",
        "templates_scanned": total,
        "template_files": scanned,
        "conventions": [C[k].resolve(total) for k in
                        ["language", "numbering", "defined", "preamble", "annex",
                         "signature", "law", "forum", "date"]],
        "party_labels": [{"label": l, "templates": n} for l, n in party_votes.most_common(8)],
        "confirmation_required": [],
        "disclaimer": ("המוסכמות נלמדו בספירה אוטומטית מהתבניות של הלקוח, והדף הנלווה אומר על כמה מסמכים כל "
                       "אחת נשענת. מוסכמה שנויה נשאלת בשאלה אחת בסבב השאלות, ואחרי התשובה הטיוטה נמסרת "
                       "נקייה, בלי המתנה לאישור עורך דין."),
    }
    # הדין שנלמד, בקוד האחיד (meta.governing_law בטיוטה). רק ממוסכמה מבוססת; אחרת None והדין נשאל
    import governing_law as GL
    law_c = next((c for c in out["conventions"] if c.get("value") and str(c["value"]).startswith("דיני ")
                  and c.get("status") not in ("שנויה", "טעונה אישור", "לא נלמדה")), None)
    out["governing_law"] = GL.code(law_c["value"]) if law_c else None
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
