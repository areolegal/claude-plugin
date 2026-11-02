# -*- coding: utf-8 -*-
"""מונחים עמומים: רשימה אחת, משותפת לנושא ונותן ולמעריך הסיכונים (הערות ענבל לנושא ונותן, 22.10.2026, כלל 5).

מונח עמום הוא אמת מידה בלי תוכן מוגדר. הוא מעביר את ההכרעה לבית המשפט, ובדרך כלל לטובת מי שהפר. הנושא ונותן
אינו מכניס מונח כזה לנוסח שלו בלי הפניה למבחן מוגדר (תקן, הוראות בכתב, רף מספרי, נספח), ושער האיכות מתריע
כשהוא מופיע (content_checks.py, VAGUE_TERM). מעריך הסיכונים משתמש באותה רשימה כשהוא סורק את ההסכם כולו
(r2-lenses.md, "מונחים עמומים"), ורושם כל מופע כסיכון מסוג vague_term.

    python3 vague_terms.py <corpus.json>                 # מסלול ההרצה: הפלט של extract_corpus.py, כל המסמכים
    python3 vague_terms.py <קובץ טקסט, docx או PDF>      # מסמך אחד, פסקה ופסקה

corpus.json הוא המסלול המועדף: הוא כבר מכסה Word, PDF וטקסט, ומסמך שלא נקרא מדווח ב-unreadable. PDF ישיר נקרא
דרך שכבת הטקסט (risk/page_text.py); PDF בלי שכבת טקסט או בלי ספריית PDF אינו קורס: יציאה 2 עם הסיבה.
Python 3, ספרייה סטנדרטית בלבד (קריאת docx דרך docx_tracked, ו-PDF דרך pymupdf או pypdf כשהן זמינות).

ריצה S1h (29.10.2026, ממצא 6): הרשימה הורחבה (promptly, immediately, reasonable assistance, best/reasonable
endeavours, commercially reasonable, as soon as possible, material, substantial, satisfactory, in a timely manner;
"באופן מיידי", "בהקדם", "סביר", "מהותי", "לשביעות רצון"), ולכל מופע נרשם context: המשפט שבו המונח, ולא רק
תחילת הפסקה. הסריקה אינה מסננת מופעים, גם לא בסעיף שיש בו ויתור מכוון.
"""
import io
import json
import os
import re
import sys
import unicodedata

# כל מונח: הביטוי, והאם הוא עמום רק כשאין לו אמת מידה בהמשך המשפט. הסדר חשוב: הצירוף הארוך לפני הקצר שבתוכו
# ("commercially reasonable efforts" לפני "commercially reasonable"), כך שמופע אחד נרשם פעם אחת ולא פעמיים
TERMS = [
    r"סטנדרט מחמיר", r"רמה מקצועית גבוהה", r"ברמה (?:מקצועית )?גבוהה", r"ברמה הגבוהה ביותר",
    r"כמקובל בענף", r"כמקובל בשוק", r"כנהוג בענף", r"לפי הנהוג", r"הסטנדרטים המקובלים",
    r"מאמצים מסחריים סבירים", r"מאמצים סבירים", r"מאמץ סביר", r"מיטב המאמצים", r"מירב המאמצים",
    r"מיטב מאמצי(?:ו|ה|הם)", r"כמיטב יכולת(?:ו|ה|ם)", r"בהקדם האפשרי", r"בהקדם", r"תוך זמן סביר",
    r"באופן מיידי", r"מיידית", r"באופן מקצועי ויעיל", r"שביעות רצו(?:ן|נה|נו|נם|נן)(?: (?:המלאה )?של)?",
    r"סביר(?:ה|ים|ות)?", r"מהותי(?:ת|ים|ות)?",
    r"best practices?", r"industry[- ]standard", r"industry practice", r"state of the art",
    r"high(?:est)? (?:professional )?standards?", r"(?:all )?best (?:efforts|endeavou?rs)",
    r"commercially reasonable (?:efforts|endeavou?rs)", r"commercially reasonable",
    r"(?:all )?reasonable (?:efforts|endeavou?rs)", r"(?:all )?reasonable assistance",
    r"as soon as (?:reasonably )?practicable", r"as soon as possible", r"within a reasonable time",
    r"in a timely manner", r"promptly", r"immediately",
    r"to the (?:reasonable )?satisfaction of", r"satisfactory", r"good industry practice", r"workmanlike manner",
    r"material(?:ly)?", r"substantial(?:ly)?",
]
# בעברית מותרות לפני המונח אותיות השימוש ("במאמצים סבירים", "ובהקדם האפשרי"); הן אינן חלק מ-term
VAGUE = re.compile(r"(?<![\w֐-׿])(?:[ובכלמשה]{1,2}(?=[֐-׿]))?((?:%s))(?![\w֐-׿])" % "|".join(TERMS), re.I)

# אמת מידה שהופכת את המונח למוגדר: תקן נקוב, נספח, הוראות בכתב, או מספר עם יחידה
DEFINED_TEST = re.compile(
    r"\bISO\b|\bIEC\b|\bSOC ?2\b|ת[\"״]י|תקן (?:ישראלי|בינלאומי|מס)|לפי תקן|בהתאם לתקן|"
    r"נספח|annex|schedule|exhibit|appendix|"
    r"הוראות(?:יה|יו)? בכתב|written instructions|"
    r"\d+(?:[.,]\d+)?\s*(?:%|ימים|ימי עסקים|שעות|חודשים|days|business days|hours|months)", re.I)


CONTEXT_MAX = 200   # אורך ההקשר של מופע: המשפט שבו המונח, ובמשפט ארוך חלון סביב המונח
SENT_END = re.compile(r"[.;](?=\s|$)")


def context_of(text, start, end, a=None, b=None):
    """המשפט שבו המונח (מ-a עד b), ובמשפט ארוך מ-CONTEXT_MAX חלון סביבו, בלי חצי מילה בקצוות. כך כל מופע
    נרשם עם ההקשר שלו, גם כשהוא בסוף פסקה ארוכה (קודם נרשמו 160 התווים הראשונים של הפסקה)."""
    a = 0 if a is None else a
    b = len(text) if b is None else b
    if b - a > CONTEXT_MAX:
        half = max(0, (CONTEXT_MAX - (end - start)) // 2)
        a2, b2 = max(a, start - half), min(b, end + half)
        if a2 > a and " " in text[a2:start]:
            a2 = text.index(" ", a2) + 1
        if b2 < b and " " in text[end:b2]:
            b2 = text.rindex(" ", end, b2)
        a, b = a2, b2
    return text[a:b].strip()


def find(text):
    """המונחים העמומים בטקסט. לכל מופע: term, defined (יש אמת מידה באותו משפט), start, context (המשפט סביבו).
    כל מופע נרשם, גם מונח בסעיף שיש בו ויתור מכוון: הסינון הוא של המעריך, לא של הסריקה."""
    # טקסט מ-PDF מגיע עם צירופי אותיות (ﬀ, ﬁ, ﬂ) ומקפים רכים: מנרמלים כמו בבדיקת הציטוטים (risk/page_text.py),
    # אחרת "reasonable efforts" בהסכם שחולץ מ-PDF אינו נתפס. המיקום (start) הוא בטקסט המנורמל
    text = unicodedata.normalize("NFKC", text or "").replace("­", "")
    out = []
    for m in VAGUE.finditer(text):
        a = max(text.rfind(".", 0, m.start()), text.rfind(";", 0, m.start())) + 1
        b = min([x for x in (text.find(".", m.end()), text.find(";", m.end())) if x >= 0] or [len(text)])
        # גבולות המשפט להקשר: נקודה או נקודה-פסיק ואחריהן רווח, כך ש-"15.5" ו-"18.3" אינם סוף משפט
        pre = [x.end() for x in SENT_END.finditer(text, 0, m.start())]
        nx = SENT_END.search(text, m.end())
        out.append({"term": m.group(1), "defined": bool(DEFINED_TEST.search(text[a:b])), "start": m.start(1),
                    "context": context_of(text, m.start(1), m.end(1), pre[-1] if pre else 0,
                                          nx.end() if nx else len(text))})
    return out


def undefined(text):
    """רק המונחים שאין להם אמת מידה באותו משפט."""
    return [f for f in find(text) if not f["defined"]]


def _paragraphs(path):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if path.lower().endswith(".docx"):
        from common import docx_tracked as dt
        return dt.received_paragraphs(path)
    with io.open(path, "rb") as fh:
        raw = fh.read()
    from risk.page_text import is_pdf, pdf_text   # PdfTextUnavailable עולה ל-main
    if is_pdf(raw):
        return pdf_text(raw).split("\n")
    return raw.decode("utf-8-sig", "replace").split("\n")


def _corpus_paragraphs(data):
    """(מסמך, מספר פסקה, טקסט, פרטים) מ-corpus.json: הפלט של extract_corpus.py של הרכיב
    (documents[].paragraphs[].text) או של הספרייה (רשימת מסמכים, parts{}[].text_accept_all)."""
    docs = data.get("documents") if isinstance(data, dict) else data
    if not isinstance(docs, list):
        raise ValueError("הקובץ אינו corpus.json של extract_corpus.py")
    for d in docs:
        name = d.get("path") or d.get("file") or ""
        if "paragraphs" in d:
            for n, p in enumerate(d.get("paragraphs") or []):
                yield name, p.get("i", n), p.get("text") or "", {k: p[k] for k in ("clause", "page") if p.get(k)}
        else:
            for part, paras in (d.get("parts") or {}).items():
                for n, p in enumerate(paras):
                    yield name, p.get("i", n), p.get("text_accept_all") or "", {"part": part}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv or not os.path.exists(argv[0]):
        print("שימוש: vague_terms.py <corpus.json, או קובץ טקסט, docx או PDF>")
        return 2
    hits = []
    if argv[0].lower().endswith(".json"):
        try:
            with io.open(argv[0], encoding="utf-8-sig") as fh:
                data = json.load(fh)
            rows = list(_corpus_paragraphs(data))
        except (ValueError, AttributeError) as e:
            print("corpus.json לא נקרא: %s" % e)
            return 2
        for name, i, t, extra in rows:
            for f in find(t):
                hits.append(dict({"file": name, "paragraph": i, "term": f["term"], "defined": f["defined"],
                                  "context": f["context"], "text": t[:160]}, **extra))
        for u in (data.get("unreadable") or []) if isinstance(data, dict) else []:
            print("לא נקרא, ולכן לא נסרק: %s" % u, file=sys.stderr)
    else:
        try:
            paras = _paragraphs(argv[0])
        except Exception as e:   # PDF סרוק, בלי ספריית PDF או פגום: הסיבה, בלי קריסה
            print("המסמך לא נקרא (%s). הריצו extract_corpus.py והעבירו את corpus.json" % e)
            return 2
        for i, t in enumerate(paras):
            for f in find(t):
                hits.append({"paragraph": i, "term": f["term"], "defined": f["defined"], "context": f["context"],
                             "text": t[:160]})
    print(json.dumps(hits, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
