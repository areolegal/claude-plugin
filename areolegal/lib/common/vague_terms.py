# -*- coding: utf-8 -*-
"""מונחים עמומים: רשימה אחת, משותפת לנושא ונותן ולמעריך הסיכונים (הערות ענבל לנושא ונותן, 22.10.2026, כלל 5).

מונח עמום הוא אמת מידה בלי תוכן מוגדר. הוא מעביר את ההכרעה לבית המשפט, ובדרך כלל לטובת מי שהפר. הנושא ונותן
אינו מכניס מונח כזה לנוסח שלו בלי הפניה למבחן מוגדר (תקן, הוראות בכתב, רף מספרי, נספח), ושער האיכות מתריע
כשהוא מופיע (content_checks.py, VAGUE_TERM). מעריך הסיכונים משתמש באותה רשימה כשהוא סורק את ההסכם כולו
(methodology.md, "מונחים עמומים"), ורושם כל מופע כסיכון מסוג vague_term.

    python3 vague_terms.py <קובץ טקסט או docx>      # כל המופעים, פסקה ופסקה

Python 3, ספרייה סטנדרטית בלבד (קריאת docx דרך docx_tracked כשהיא זמינה).
"""
import io
import json
import os
import re
import sys

# כל מונח: הביטוי, והאם הוא עמום רק כשאין לו אמת מידה בהמשך המשפט
TERMS = [
    r"סטנדרט מחמיר", r"רמה מקצועית גבוהה", r"ברמה (?:מקצועית )?גבוהה", r"ברמה הגבוהה ביותר",
    r"כמקובל בענף", r"כמקובל בשוק", r"כנהוג בענף", r"לפי הנהוג", r"הסטנדרטים המקובלים",
    r"מאמצים סבירים", r"מיטב המאמצים", r"מאמצים מסחריים סבירים", r"בהקדם האפשרי", r"תוך זמן סביר",
    r"באופן מקצועי ויעיל", r"שביעות רצון(?:ה|ו)? (?:המלאה )?של",
    r"best practices?", r"industry[- ]standard", r"industry practice", r"state of the art",
    r"high(?:est)? (?:professional )?standards?", r"best efforts", r"commercially reasonable efforts",
    r"reasonable efforts", r"as soon as (?:reasonably )?practicable", r"within a reasonable time",
    r"to the (?:reasonable )?satisfaction of", r"good industry practice", r"workmanlike manner",
]
VAGUE = re.compile(r"(?<![\w֐-׿])(?:%s)(?![\w֐-׿])" % "|".join(TERMS), re.I)

# אמת מידה שהופכת את המונח למוגדר: תקן נקוב, נספח, הוראות בכתב, או מספר עם יחידה
DEFINED_TEST = re.compile(
    r"\bISO\b|\bIEC\b|\bSOC ?2\b|ת[\"״]י|תקן (?:ישראלי|בינלאומי|מס)|לפי תקן|בהתאם לתקן|"
    r"נספח|annex|schedule|exhibit|appendix|"
    r"הוראות(?:יה|יו)? בכתב|written instructions|"
    r"\d+(?:[.,]\d+)?\s*(?:%|ימים|ימי עסקים|שעות|חודשים|days|business days|hours|months)", re.I)


def find(text):
    """המונחים העמומים בטקסט. לכל מופע: term, defined (יש אמת מידה באותו משפט), start."""
    out = []
    for m in VAGUE.finditer(text or ""):
        a = max(text.rfind(".", 0, m.start()), text.rfind(";", 0, m.start())) + 1
        b = min([x for x in (text.find(".", m.end()), text.find(";", m.end())) if x >= 0] or [len(text)])
        out.append({"term": m.group(0), "defined": bool(DEFINED_TEST.search(text[a:b])), "start": m.start()})
    return out


def undefined(text):
    """רק המונחים שאין להם אמת מידה באותו משפט."""
    return [f for f in find(text) if not f["defined"]]


def _paragraphs(path):
    if path.lower().endswith(".docx"):
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from common import docx_tracked as dt
        return dt.received_paragraphs(path)
    with io.open(path, encoding="utf-8") as fh:
        return fh.read().split("\n")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or not os.path.exists(argv[0]):
        print("שימוש: vague_terms.py <קובץ טקסט או docx>")
        return 2
    hits = []
    for i, t in enumerate(_paragraphs(argv[0])):
        for f in find(t):
            hits.append({"paragraph": i, "term": f["term"], "defined": f["defined"], "text": t[:160]})
    print(json.dumps(hits, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
