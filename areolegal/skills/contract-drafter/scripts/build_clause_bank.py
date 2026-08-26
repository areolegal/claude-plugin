# -*- coding: utf-8 -*-
"""
בונה בנק סעיפים מנוסח הלקוח עצמו, מתוך התבניות המאושרות שבמרשם.

התכלית: כשהרכיב מנסח סעיף שיפוי, סעיף סודיות או סעיף סיום, עליו לכתוב אותם
בלשון שהחברה הזאת כותבת בה בפועל, ולא בלשון כללית שנשמעת נכון. כל רשומה בבנק
היא נוסח שנלקח כלשונו ממסמך מאושר, עם שם המסמך ומספר הסעיף, כדי שאפשר לחזור למקור.

הבנק אינו גובר על הפלייבוק. סדר העדיפות בניסוח:
  1. playbook-core.json, הנוסח המאושר והקו האדום
  2. בנק הסעיפים, לשון הבית בפועל
  3. ניסוח חדש, ורק כשאין לא זה ולא זה, ואז הוא מסומן כנוסח חדש

הרצה:
  python3 build_clause_bank.py --registry <path/template-registry.json> --out <path/clause-bank.json>
"""
import argparse
import io
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_template_registry import docx_text, docx_paragraphs  # noqa: E402


# כותרת סעיף. הזיהוי נעשה על פסקאות ולא על טקסט משוטח: בטקסט משוטח אי אפשר
# לדעת היכן נגמרת הכותרת ומתחיל הגוף, והתוצאה היא כותרות קטועות בנות מילה אחת.
HEADING_INLINE = re.compile(
    r"^(?:סעיף\s+)?(\d+(?:\.\d+)*)\s*[:\.\)]\s*(.{2,70}?)\s*$")
HEADING_SPLIT = re.compile(
    r"^(?:סעיף\s+)?(\d+(?:\.\d+)*)\s*[:\.\)]\s+(.{2,70}?)[\.:]\s+(.{40,})$", re.S)

# רשימת הנושאים מכסה גם משפחות שאינן הסכם שירותים: הפצה, זכיינות, חכירה,
# ליסינג, שכירות מסחרית ורישוי. כותרת אמיתית בנייר ישראלי כמעט תמיד תיפול לאחד מאלה.
TOPICS = [
    ("הגדרות ופרשנות", ["הגדרות", "פרשנות", "definitions", "interpretation"]),
    ("מהות ההתקשרות והיקפה", ["מהות ההתקשרות", "היקף ההתקשרות", "היקף השירותים", "מתן השירותים",
                              "מתן הרישיון", "היקף הרישיון", "מהות ההסכם", "המושכר",
                              "מסירת הציוד", "מסירת המושכר", "scope of", "the services", "appointment", "grant of rights", "engagement", "scope", "the services"]),
    ("תקופה, חידוש וסיום", ["תקופת", "סיום", "פקיעה", "השבה", "ביטול ההסכם", "חידוש",
                            "הודעה מוקדמת", "השעיה", "term and termination", "termination",
                            "renewal", "expiration", "term", "effect of termination", "suspension"]),
    ("אופציות והארכה", ["אופציה", "אופציית", "מימוש האופציה", "הארכת ההתקשרות", "זכות סירוב",
                        "option to", "right of first refusal"]),
    ("תמורה ותנאי תשלום", ["תמורה", "תשלום", "תמלוגים", "דמי שכירות", "דמי חכירה", "דמי ליסינג",
                           "דמי מנוי", "דמי ניהול", "פרמיה", "מחירון", "הצמדה", "ריבית פיגורים",
                           "התחשבנות", "payment", "fees", "consideration", "royalt", "price", "pricing", "invoic", "discount", "taxes"]),
    ("סודיות", ["סודיות", "מידע סודי", "אי גילוי", "היקף החשיפה", "השבת המידע", "השמדת",
                "גילוי הנדרש", "גילוי על פי דין", "confidential"]),
    ("קניין רוחני ומותג", ["קניין רוחני", "זכויות יוצרים", "סימני מסחר", "המותג", "רישיון שימוש",
                           "שימוש מותר", "בעלות בנתונים", "intellectual property", "trademark", "proprietary rights", "ownership", "branding", "marks"]),
    ("אחריות והגבלתה", ["הגבלת אחריות", "גבולות אחריות", "אחריות והגבלתה", "אחריות הצדדים",
                        "תקרת אחריות", "נזק תוצאתי", "limitation of liability", "disclaimer", "limited liability", "limitation on liability", "no consequential", "disclaimer of warranties"]),
    ("אחריות למוצר וריקול", ["חבות מוצר", "אחריות למוצר", "ריקול", "recall", "product liability"]),
    ("שיפוי", ["שיפוי", "לשפות", "indemnif"]),
    ("ביטוח", ["ביטוח", "פוליסה", "אישור קיום ביטוחים", "חובת גילוי", "מקרה ביטוח", "insurance"]),
    ("הגנת הפרטיות ואבטחת מידע", ["הגנת הפרטיות", "מידע אישי", "אבטחת מידע", "עיבוד מידע",
                                  "gdpr", "data protection", "personal data", "privacy", "security", "dpa"]),
    ("ציות, אנטי שוחד וסנקציות", ["ציות", "אנטי שוחד", "שחיתות", "סנקציות", "אמברגו",
                                  "anti-bribery", "compliance", "sanctions", "anti-corruption", "export law", "export control", "trade compliance"]),
    ("רמת שירות, תמיכה ותחזוקה", ["רמת שירות", "sla", "זמני תגובה", "תמיכה", "זמינות",
                                  "תחזוקה", "תקלות", "תיקונים", "service level", "maintenance", "support", "maintenance and support", "availability"]),
    ("אי תחרות ואי שידול", ["אי תחרות", "אי-תחרות", "אי שידול", "אי-שידול", "הגבלת עיסוק",
                            "non-compete", "non-solicit", "no solicitation"]),
    ("בלעדיות וטריטוריה", ["בלעדיות", "הטריטוריה", "טריטוריאלית", "אזור", "exclusivity",
                           "territory", "exclusive", "non-exclusive", "territory"]),
    ("יעדים, הזמנות, אספקה ומלאי", ["יעדי רכש", "יעדי מכירה", "הזמנות", "אספקה", "מלאי",
                                    "סחורה פגומה", "סיכון ובעלות", "המוצרים", "ספקים מאושרים",
                                    "purchase order", "supply", "inventory", "order process", "orders", "delivery", "forecast", "quota"]),
    ("שיווק, קידום וסטנדרטים", ["שיווק", "קידום מכירות", "פרסום", "קרן שיווק", "ספר התפעול",
                                "סטנדרטים", "בקרת איכות", "הדרכה", "marketing", "standards", "promotion", "training", "demand generation"]),
    ("דיווח, ספרים וביקורת", ["דיווח", "ספרים", "ביקורת", "audit", "reporting", "books and records", "reports", "records", "audit rights"]),
    ("התחייבויות הצדדים", ["התחייבויות", "מצגים", "מצג", "יחסי הצדדים", "היעדר מצג",
                           "representations", "warranties", "undertakings", "obligations", "covenants", "reseller obligations"]),
    ("ערבויות וביטחונות", ["ערבות", "ביטחונות", "פיקדון", "שטר חוב", "guarantee", "security deposit"]),
    ("קיזוז ועיכבון", ["קיזוז", "עיכבון", "set-off", "lien"]),
    ("המחאה, הסבה ושכירות משנה", ["המחאת", "הסבת", "העברת זכויות", "איסור העברה", "שכירות משנה",
                                  "העברת הזכויות", "assignment", "sublease"]),
    ("שינויים והתאמות", ["שינויים", "התאמות", "שינוי ההסכם", "amendment", "change order"]),
    ("כוח עליון", ["כוח עליון", "force majeure"]),
    ("הפרה, סעדים ותרופות", ["הפרה", "סעדים", "תרופות", "פיצוי מוסכם", "breach", "remedies"]),
    ("הודעות", ["הודעות", "מסירת הודעות", "notices", "notice"]),
    ("דין, סמכות שיפוט ויישוב מחלוקות", ["דין וסמכות", "סמכות שיפוט", "הדין החל", "בוררות",
                                         "יישוב מחלוקות", "governing law", "jurisdiction",
                                         "dispute resolution", "arbitration"]),
    ("שונות", ["שונות", "שלמות ההסכם", "ויתור", "נפרדות", "כותרות", "miscellaneous",
               "entire agreement", "severability", "waiver"]),
]


def norm(s):
    """מנרמל מקף ורווח, כדי ש'אי-תחרות' ו'אי תחרות' ייחשבו אותו מונח."""
    return re.sub(r"[\-־–]", " ", s.lower())


def topic_of(heading, body):
    h = norm(heading)
    for label, words in TOPICS:
        for w in words:
            if norm(w) in h:
                return label, "כותרת הסעיף"
    b = norm(body[:600])
    best, best_n = None, 0
    for label, words in TOPICS:
        n = sum(b.count(norm(w)) for w in words)
        if n > best_n:
            best, best_n = label, n
    if best_n >= 2:
        return best, "גוף הסעיף, טעון אישור"
    return None, None


NOT_A_HEADING = re.compile(
    r"^\d{1,2}\.\d{1,2}\.\d{4}$|₪|^\d+$|בין הצדדים|מצד אחד|"
    # כותרת המסמך ופסקאות המבוא אינן סעיפים
    r"^(?:reseller|master|mutual|software|services?|distribution|license)?\s*(?:agreement|contract)\s*$|"
    r"^witnesseth|^background\s*$|^recitals?\s*$|^preamble\s*$|^הואיל\s*$", re.I)


# כותרת בלי מספר. במסמכים שממוספרים אוטומטית ב-Word, המספר אינו קיים כטקסט,
# והכותרת היא פסקה קצרה בלבד. זיהוי לפי מספר בתחילת פסקה מחמיץ אותם לגמרי,
# וזה בדיוק המבנה של כמעט כל הסכם מסחרי באנגלית.
def looks_like_bare_heading(p):
    p = p.strip().rstrip(".:")
    if not (3 <= len(p) <= 70):
        return False
    if p.endswith((",", ";")) or p.count(" ") > 8:
        return False
    words = [w for w in re.split(r"\s+", p) if w]
    if not words:
        return False
    latin = [w for w in words if re.match(r"^[A-Za-z]", w)]
    if latin and len(latin) == len(words):
        # ALL CAPS או Title Case, ולא משפט רגיל
        if p.isupper():
            return True
        caps = sum(1 for w in words if w[:1].isupper())
        if caps >= max(1, len(words) - 1):
            return True
        return False
    # עברית: פסקה קצרה בלי פועל בסוף משפט ובלי נקודה
    if re.search(r"[֐-׿]", p) and not p.endswith("."):
        return True
    return False


def split_clauses(paras):
    """מחזיר רשימת (מספר, כותרת, גוף) מתוך פסקאות המסמך.
       כותרת היא פסקה קצרה הפותחת במספר סעיף; הגוף הוא כל מה שעד הכותרת הבאה.
       כשהכותרת והגוף יושבים באותה פסקה, הם מופרדים בנקודה או בנקודתיים."""
    heads = []   # (index, num, heading, inline_body)
    for i, p in enumerate(paras):
        if NOT_A_HEADING.search(p.strip()):
            continue
        m = HEADING_INLINE.match(p.strip())
        if m and not re.match(r"^\d{1,2}\.\d{1,2}\.\d{4}", p.strip()):
            heads.append((i, m.group(1), m.group(2).strip(" :.-"), ""))
            continue
        m = HEADING_SPLIT.match(p.strip())
        if m:
            heads.append((i, m.group(1), m.group(2).strip(" :.-"), m.group(3).strip()))
            continue
        # כותרת בלי מספר, ובלבד שאחריה גוף ממשי ולא כותרת נוספת
        if looks_like_bare_heading(p) and i + 1 < len(paras) and len(paras[i + 1]) > 120:
            heads.append((i, None, p.strip().rstrip(".:"), ""))
    out = []
    for j, (i, num, head, inline) in enumerate(heads):
        end = heads[j + 1][0] if j + 1 < len(heads) else len(paras)
        body = " ".join([inline] + paras[i + 1:end]).strip()
        body = re.sub(r"\s+", " ", body)
        if len(head) < 3 or len(body) < 60:
            continue
        out.append((num, head, body))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--registry", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-chars", type=int, default=2500,
                    help="אורך מרבי לנוסח שנשמר, כדי שהבנק לא יתנפח")
    args = ap.parse_args()

    reg = json.load(io.open(args.registry, encoding="utf-8"))
    docs = [d for d in reg.get("documents", []) if d.get("approved_current")]
    if not docs:
        print("אין תבניות מאושרות במרשם. יש להריץ תחילה את build_template_registry.py.")
        sys.exit(2)

    entries, unmatched = [], []
    for d in docs:
        path = os.path.join(d.get("folder", ""), d["file"])
        if path.lower().endswith(".docx"):
            # ב-redline קוראים את הנוסח שאחרי קבלת השינויים; קריאה גולמית
            # משרגת את הישן והחדש ומייצרת סעיפים משובשים
            mode = "base" if d.get("approved_current_basis") == "redline_base" else "final"
            paras = docx_paragraphs(path, mode=mode)
        else:
            paras = io.open(path, encoding="utf-8", errors="ignore").read().split("\n")
        if not paras:
            continue
        for num, head, body in split_clauses(paras):
            topic, basis = topic_of(head, body)
            rec = {
                "topic": topic,
                "topic_basis": basis,
                "heading": head,
                "clause_number": num,
                "source_file": d["file"],
                "source_folder": d.get("folder"),
                "family": d.get("family"),
                "company_role_candidates": d.get("company_role_candidates", []),
                # מאיזה צד נכתב הנוסח. סעיף שנכתב מצד הספק אינו לשון הבית של
                # מפיץ, ושימוש בו כברירת מחדל מנסח את ההסכם נגד האינטרס שלנו.
                "side": ("טעון בירור: המסמך הוא redline ולא נקבע מי סימן את השינויים"
                         if d.get("approved_current_basis") == "redline_base"
                         else "נייר הלקוח"),
                "usable_as_house_wording": d.get("approved_current_basis") != "redline_base",
                "language": d.get("language"),
                "text": body[:args.max_chars],
                "truncated": len(body) > args.max_chars,
            }
            (entries if topic else unmatched).append(rec)

    by_topic = {}
    for e in entries:
        by_topic.setdefault(e["topic"], []).append(e)
    # בכל נושא, הנוסח הארוך והמפורט ראשון: הוא בדרך כלל המלא ולא ההפניה
    for k in by_topic:
        by_topic[k].sort(key=lambda x: -len(x["text"]))

    out = {
        "generated_at": date.today().strftime("%d.%m.%Y"),
        "source": "נוסחים שנלקחו כלשונם מהתבניות המאושרות של הלקוח",
        "templates_used": [d["file"] for d in docs],
        "topics_found": sorted(by_topic.keys()),
        "topics_missing": [t for t, _ in TOPICS if t not in by_topic],
        "clauses": entries,
        "unmatched_clauses": [{"heading": u["heading"], "clause_number": u["clause_number"],
                               "source_file": u["source_file"]} for u in unmatched],
        "precedence": ("הפלייבוק גובר על בנק הסעיפים. הבנק גובר על ניסוח חדש. "
                       "נוסח שנושאו נקבע לפי גוף הסעיף בלבד טעון אישור לפני שימוש."),
        "side_warning": ("סעיף שסומן usable_as_house_wording=false נלקח ממסמך שלא נקבע "
                         "מאיזה צד הוא מנוסח. אין להשתמש בו כלשון בית ואין להכניסו "
                         "לטיוטה לפני שהמשתמש קבע מי סימן את השינויים במסמך המקור. "
                         "הכנסת נוסח שנכתב מצד הספק להסכם שבו הלקוח הוא המפיץ מנסחת "
                         "את ההסכם נגד האינטרס של הלקוח."),
        "unresolved_side": sorted({e["source_file"] for e in entries
                                   if not e["usable_as_house_wording"]}),
    }
    dd = os.path.dirname(os.path.abspath(args.out))
    if dd and not os.path.isdir(dd):
        os.makedirs(dd)
    io.open(args.out, "w", encoding="utf-8").write(
        json.dumps(out, ensure_ascii=False, indent=2))

    print("נאספו %d סעיפים מתוך %d תבניות מאושרות, ב-%d נושאים"
          % (len(entries), len(docs), len(by_topic)))
    for k in sorted(by_topic, key=lambda x: -len(by_topic[x])):
        print("  %-30s %d נוסחים" % (k, len(by_topic[k])))
    if out["topics_missing"]:
        print("נושאים שאין להם נוסח בית: " + ", ".join(out["topics_missing"]))
    if unmatched:
        print("%d סעיפים לא שויכו לנושא ונשמרו לעיון" % len(unmatched))


if __name__ == "__main__":
    main()
