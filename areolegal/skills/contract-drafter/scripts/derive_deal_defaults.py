# -*- coding: utf-8 -*-
"""
גוזר את ברירות המחדל המסחריות של הלקוח מתוך ההסכמים שלו עצמו.

התכלית היא לא לשאול את מה שאפשר לדעת. במקום לשאול "מהם תנאי התשלום",
הרכיב אומר: "בניירות שלך שוטף פלוס 45 מופיע בשישה מתוך תשעה הסכמים, לאשר או לשנות".
שאלה שאפשר להשיב עליה מהתיקייה היא שאלה מיותרת, והיא שוחקת את סבלנות המשתמש
לפני שהגיעו לשאלות שבאמת חשובות.

שיטת החילוץ: לכל פרמטר יש עוגן נושאי, והערך נחפש רק בחלון שסביב העוגן.
בלי עוגן, "12 חודשים" בסעיף אי תחרות נספר כתקופת ההסכם, וזאת טעות שמייצרת
ברירת מחדל שגויה במסמך משפטי.

כל ערך נגזר בספירה, נרשם עם מספר ההסכמים התומכים ועם ציטוט מקור,
ואינו הופך לברירת מחדל בלי אישור המשתמש.

הרצה:
  python3 derive_deal_defaults.py --registry <template-registry.json> --out <deal-defaults.json>
"""
import argparse
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_text, docx_paragraphs  # noqa: E402

WINDOW = 420   # תווים סביב העוגן


def R(*parts):
    return re.compile("|".join(parts), re.I)


SPELLED = re.compile(r"[A-Za-z\u0590-\u05FF]+[\s\-]*\(\s*(\d{1,4})\s*\)")


def normalize(t):
    """מנרמל את הכתיב המשפטי של מספרים.

    נייר משפטי באנגלית כותב "within thirty (30) days", ובעברית "תוך שלושים (30) יום".
    ביטוי שמחפש ספרה מיד אחרי המילה מחמיץ את כל אלה, וזו הסיבה שגזירה מקורפוס
    אנגלי החזירה כמעט כלום. כאן המילה נמחקת והספרה שבסוגריים נשארת.
    """
    return SPELLED.sub(r"\1", t)


# (שם, עוגן נושאי, ביטוי הערך, יחידה, מה זה אומר למשתמש)
PARAMS = [
    ("תנאי תשלום",
     R(r"תנאי\s+ה?תשלום", r"שוטף\s*\+", r"מועד\s+ה?תשלום", r"חשבונית",
       r"payment\s+terms", r"\bnet\s+\d",
       r"payment\s+terms", r"\bnet\s+\d", r"invoice", r"due\s+and\s+payable"),
     R(r"שוטף\s*\+?\s*(\d{1,3})", r"(?:תוך|בתוך|בטרם|לא\s+יאוחר\s+מ)\s*(\d{1,3})\s+ימים?",
       r"\bnet\s+(\d{1,3})\b",
       r"\bnet\s+(\d{1,3})\b", r"within\s+(\d{1,3})\s+days", r"(\d{1,3})\s+days\s+of\s+(?:the\s+)?invoice"),
     "ימים", "כמה ימים מקבלת החשבונית ועד התשלום"),

    ("הודעה מוקדמת לסיום",
     R(r"סיום\s+ה?הסכם", r"לסיים\s+את\s+ה?הסכם", r"אי[\s\-־]?חידוש", r"ביטול\s+ה?הסכם",
       r"הודעה\s+מוקדמת", r"termination\s+for\s+convenience",
       r"terminat", r"non[\s\-]?renewal", r"for\s+convenience", r"prior\s+written\s+notice"),
     R(r"(\d{1,3})\s+ימים?\s+מראש", r"של\s+(\d{1,3})\s+ימים?",
       r"לפחות\s+(\d{1,3})\s+ימים?", r"(\d{1,2})\s+חודשים?\s+מראש",
       r"(\d{1,3})\s+days['’]?\s+(?:prior\s+)?written\s+notice", r"(?:at\s+least\s+)?(\d{1,3})\s+days['’]?\s+notice", r"(\d{1,2})\s+months['’]?\s+(?:prior\s+)?notice"),
     "ימים", "כמה ימי הודעה מראש נדרשים לסיום ההתקשרות"),

    ("תקופת ריפוי הפרה",
     R(r"הפרה\s+יסודית", r"לא\s+תוקנה", r"תוקנה\s+ה?הפרה", r"תקופת\s+ריפוי",
       r"cure\s+period",
       r"material\s+breach", r"cure\s+period", r"fails?\s+to\s+cure", r"remed(?:y|ied)"),
     R(r"(?:בתוך|תוך)\s+(\d{1,3})\s+ימים?", r"(\d{1,3})\s+ימים?\s+ממועד\s+ה?הודעה",
       r"within\s+(\d{1,3})\s+days",
       r"within\s+(\d{1,3})\s+days", r"(\d{1,3})[\s\-]day\s+cure"),
     "ימים", "כמה ימים לתיקון הפרה לפני שהיא מזכה בביטול"),

    ("תקופת ההתקשרות הראשונה",
     R(r"תקופת\s+ה?(?:הסכם|התקשרות|שכירות|חכירה|ליסינג|רישיון|ביטוח)",
       r"ההסכם\s+יעמוד\s+בתוקפו", r"initial\s+term",
       r"initial\s+term", r"this\s+agreement\s+shall\s+(?:commence|be\s+effective)",
       r"continue\s+in\s+(?:full\s+force|effect)", r"shall\s+remain\s+in\s+effect",
       r"term\s+of\s+this\s+agreement"),
     R(r"(?:של|למשך|בת)\s+(\d{1,3})\s+חודשים?", r"(?:של|למשך|בת)\s+(\d{1,2})\s+שנים?",
       r"(\d{1,3})\s+חודשים?", r"(\d{1,2})\s+שנים?",
       r"(?:period|term)\s+of\s+(\d{1,3})\s+(?:months?|years?)",
       r"(?:for|of)\s+(\d{1,3})\s+months?", r"(?:for|of)\s+(\d{1,2})\s+years?",
       r"(\d{1,2})\s+years?\s+from", r"(\d{1,3})\s+months?\s+from"),
     "חודשים או שנים", "אורך התקופה הראשונה של ההתקשרות"),

    ("הארכה אוטומטית",
     R(r"תוארך\s+אוטומטית", r"חידוש\s+אוטומטי", r"יתחדש\s+מאליו",
       r"automatically\s+renew", r"אלא\s+אם\s+הודיע",
       r"automatically\s+renew", r"successive", r"unless\s+either\s+party", r"renewal\s+term"),
     R(r"(?:נוספ(?:ת|ות)\s+)?(?:בת|של)\s+(\d{1,3})\s+(?:חודשים?|שנים?)",
       r"(\d{1,3})\s+חודשים?", r"(\d{1,2})\s+שנים?",
       r"(?:successive|additional|further)\s+(?:periods?|terms?)\s+of\s+(\d{1,3})\s+(?:months?|years?)", r"(\d{1,2})[\s\-]year\s+(?:renewal|period)", r"(\d{1,3})[\s\-]month\s+(?:renewal|period)"),
     "חודשים או שנים", "אורך תקופת ההארכה האוטומטית"),

    ("תקרת אחריות",
     R(r"הגבלת\s+אחריות", r"גבולות\s+אחריות", r"תקרת\s+ה?אחריות",
       r"אחריות(?:ו|ה|ם)?\s+ה?כוללת", r"אחריות(?:ו|ה|ם)?\s+ה?מצטברת",
       r"limitation\s+of\s+liability", r"aggregate\s+liability",
       r"limitation\s+of\s+liability", r"aggregate\s+liability", r"total\s+liability", r"limited\s+liability", r"in\s+no\s+event"),
     R(r"ששולמ(?:ו|ה)\s+ב[\-]?(\d{1,2})\s+ה?חודשים",
       r"(\d{1,2})\s+ה?חודשים\s+שקדמו",
       r"לא\s+תעלה\s+על\s+(?:סך\s+)?(?:של\s+)?([\d,]{3,})",
       r"פי\s+(\d{1,2})\s+מ", r"מוגבלת\s+ל(?:סך\s+)?([\d,]{3,})",
       r"(\d{1,2})\s+חודשי\s+תמורה",
       r"(נזק\s+עקיף)",
       r"(?:fees|amounts)\s+paid[^.]{0,60}?(\d{1,2})\s+months", r"(\d{1,2})\s+months\s+(?:preceding|prior)", r"exceed[^.]{0,40}?\$\s?([\d,]{4,})", r"(indirect,?\s+consequential)"),
     "סכום או מכפיל", "כיצד מוגבלת האחריות בניירות שלך"),

    ("גבול אחריות ביטוחי",
     R(r"אישור\s+קיום\s+ביטוח", r"גבול\s+אחריות", r"סכום\s+ביטוח", r"פוליס",
       r"ביטוח\s+אחריות", r"insurance",
       r"insurance", r"policy\s+limits?", r"commercial\s+general\s+liability"),
     R(r"([\d,]{6,})\s*ש\"ח", r"בגבול\s+אחריות\s+של\s+([\d,]{4,})",
       r"סכום\s+ביטוח\s+של\s+([\d,]{4,})", r"\$\s*([\d,]{4,})",
       r"\$\s?([\d,]{5,})", r"USD\s?([\d,]{5,})"),
     'ש"ח', "גבול האחריות הביטוחי הנדרש"),

    ("ריבית פיגורים",
     R(r"ריבית\s+פיגורים", r"פיגור\s+בתשלום", r"איחור\s+בתשלום", r"late\s+payment",
       r"late\s+payment", r"overdue", r"interest\s+on"),
     R(r"(\d{1,2}(?:\.\d+)?)\s*%", r"בשיעור\s+של\s+(\d{1,2}(?:\.\d+)?)",
       r"(\d{1,2}(?:\.\d+)?)\s*%\s*per\s+(?:month|annum)", r"(\d{1,2}(?:\.\d+)?)\s*%"),
     "אחוז", "שיעור ריבית הפיגורים הנהוג"),

    ("תמלוגים או עמלה",
     R(r"תמלוגים", r"עמלה", r"royalt", r"commission",
       r"royalt", r"commission", r"discount", r"margin", r"reseller\s+price"),
     R(r"בשיעור\s+(?:של\s+)?(\d{1,2}(?:\.\d+)?)\s*%", r"(\d{1,2}(?:\.\d+)?)\s*%",
       r"(\d{1,2}(?:\.\d+)?)\s*%"),
     "אחוז", "שיעור התמלוגים או העמלה"),

    ("שרידות חובת הסודיות",
     R(r"סודיות", r"מידע\s+סודי", r"confidentialit",
       r"confidential", r"survive"),
     R(r"(\d{1,2})\s+שנים?\s+מ(?:מועד\s+)?(?:ה?סיום|תום)",
       r"למשך\s+(\d{1,2})\s+שנים?", r"(\d{1,2})\s+years?\s+(?:after|following)",
       r"(\d{1,2})\s+years?\s+(?:after|following|from)", r"period\s+of\s+(\d{1,2})\s+years?"),
     "שנים", "כמה זמן שורדת חובת הסודיות אחרי הסיום"),

    ("אי תחרות",
     R(r"אי[\s\-־]?תחרות", r"לא\s+יתחרה", r"הגבלת\s+עיסוק", r"non[\s\-]?compet",
       r"non[\s\-]?compet", r"shall\s+not\s+compete", r"no\s+solicitation"),
     R(r"(\d{1,2})\s+חודשים?", r"(\d{1,2})\s+שנים?",
       r"(\d{1,2})\s+(?:months?|years?)"),
     "חודשים או שנים", "משך הגבלת אי התחרות"),

    ("מקדמה או פיקדון",
     R(r"פיקדון", r"מקדמה", r"ערבות\s+בנקאית", r"בטוחה", r"security\s+deposit",
       r"deposit", r"advance\s+payment", r"prepayment", r"bank\s+guarantee"),
     R(r"([\d,]{4,})\s*ש\"ח", r"בסך\s+(?:של\s+)?([\d,]{4,})",
       r"(\d{1,2})\s+חודשי\s+(?:שכירות|דמי)",
       r"\$\s?([\d,]{4,})", r"([\d,]{4,})\s*(?:USD|dollars)"),
     "סכום", "גובה הפיקדון או הערבות הנהוג"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--all-documents", action="store_true",
                    help="לגזור מכל המסמכים החוזיים ולא רק מהתבניות המאושרות")
    args = ap.parse_args()

    reg = json.load(io.open(args.registry, encoding="utf-8"))
    docs = reg.get("documents", [])
    if not args.all_documents:
        docs = [d for d in docs if d.get("approved_current")]
    if not docs:
        print("אין מסמכים לגזירה. יש להריץ תחילה את build_template_registry.py.")
        sys.exit(2)

    texts = []
    for d in docs:
        p = os.path.join(d.get("folder", ""), d["file"])
        if p.lower().endswith(".docx"):
            # ב-redline הטקסט הגולמי משרג ישן וחדש; קוראים את הנוסח המתאים
            mode = "base" if d.get("approved_current_basis") == "redline_base" else "final"
            t = " ".join(docx_paragraphs(p, limit=20000, mode=mode))
        else:
            t = io.open(p, encoding="utf-8", errors="ignore").read()
        if t:
            texts.append((d["file"], d.get("family"), normalize(t)))

    results = []
    for name, anchor, value_rx, unit, explain in PARAMS:
        votes, evidence, per_doc = Counter(), {}, {}
        for fname, family, t in texts:
            found = set()
            for am in anchor.finditer(t):
                win_start = max(0, am.start() - WINDOW // 3)
                window = t[win_start:am.start() + WINDOW]
                for m in value_rx.finditer(window):
                    val = next((g for g in m.groups() if g), None)
                    if not val:
                        continue
                    val = val.replace(",", "")
                    found.add(val)
                    evidence.setdefault(val, {
                        "source_file": fname, "family": family,
                        "quote": re.sub(r"\s+", " ", window[
                            max(0, m.start() - 90):m.start() + 130]).strip()})
            if found:
                per_doc[fname] = sorted(found)
            for v in found:
                votes[v] += 1
        if not votes:
            results.append({"parameter": name, "unit": unit, "question": explain,
                            "value": None, "status": "לא נגזר",
                            "note": "לא אותר בניירות של הלקוח, יש לשאול את המשתמש"})
            continue
        ranked = votes.most_common()
        top_val, top_n = ranked[0]
        if len(ranked) > 1 and ranked[1][1] == top_n:
            status = "שנוי, יותר מערך שכיח אחד"
        elif top_n >= 2:
            status = "מבוסס"
        else:
            status = "מופע יחיד, טעון אישור"
        ev = evidence.get(top_val, {})
        results.append({
            "parameter": name, "unit": unit, "question": explain,
            "value": top_val, "status": status,
            "support": "%d מתוך %d מסמכים" % (top_n, len(texts)),
            "distribution": [{"value": v, "documents": n} for v, n in ranked[:6]],
            "per_document": per_doc,
            "source_file": ev.get("source_file"),
            "source_family": ev.get("family"),
            "quote": ev.get("quote"),
        })

    out = {
        "generated_at": date.today().strftime("%d.%m.%Y"),
        "documents_scanned": len(texts),
        "scope": "כל המסמכים החוזיים" if args.all_documents else "תבניות מאושרות בלבד",
        "source": "נגזר מהניירות של הלקוח, אינו ברירת מחדל כללית",
        "method": ("לכל פרמטר עוגן נושאי, והערך נחפש רק בחלון שסביבו. "
                   "ערך שאותר מחוץ להקשרו אינו נספר."),
        "parameters": results,
        "usage_rule": ("ערך נגזר מוצג למשתמש לאישור או לשינוי, ואינו נכנס לטיוטה בלי אישור. "
                       "ערך שסטטוסו שנוי או מופע יחיד מוצג כשאלה ולא כברירת מחדל. "
                       "כשקיים פלייבוק, עמדת הפלייבוק גוברת על הערך הנגזר. "
                       "הפיזור בין ההסכמים חשוב לא פחות מהערך השכיח: פיזור רחב "
                       "מעיד שאין לחברה עמדה אחידה, וזה עצמו ממצא."),
    }
    dd = os.path.dirname(os.path.abspath(args.out))
    if dd and not os.path.isdir(dd):
        os.makedirs(dd)
    io.open(args.out, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=2))

    print("נגזרו ברירות מחדל מ-%d מסמכים" % len(texts))
    for r in results:
        dist = ""
        if r.get("distribution") and len(r["distribution"]) > 1:
            dist = "  פיזור: " + ", ".join(
                "%s (%d)" % (x["value"], x["documents"]) for x in r["distribution"][:4])
        print("  %-26s %-8s %-22s%s" % (
            r["parameter"], (r["value"] or "לא נגזר"),
            r.get("support", ""), dist))


if __name__ == "__main__":
    main()
