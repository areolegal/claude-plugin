#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""גרסת ה-Word של דוח הסיכונים, רק לבקשת המשתמש, באותו מבנה ובאותו סדר בדיוק.

`r5-report.md`, "תוצר": ה-Word נבנה מאותו מרשם, באותו מבנה ובאותו סדר כמו
הדוח, בלי פרקים נוספים, ולעולם אינו ארוך מהדוח (הערות מעריך הסיכונים 3.6,
שינויים 1.15, 11.13, 16.5, 18.10 ו-21.3):

1. **עמוד 1, התמונה במבט אחד:** שורת הכותרת, השורה התחתונה, האם אפשר לחתום כמו
   שהוא, התמונה הכספית (עד שלוש החשיפות הגדולות
   בכסף, מול הביטוח ומול שווי העסקה), טבלת העדשות, שלושת
   המונים, המועדים הקריטיים ושורת חקר הישות. סיכון שטופל בתוך המסמך מסומן "טופל".
2. **פרק 1, הסיכונים:** טבלה אחת לפי חומרה. בהסכם הדדי, הצד בשם הסיכון.
3. **פרק 2, סתירות בין ההסכם לנספחים**, ומה גובר.
4. **פרק 3, צירופים ושרשראות.**
5. **פרק 4, הסיכונים הקריטיים בפירוט.**
6. **פרק 5, מה לא נבדק ומה חסר**, וטבלת המקורות "מה נבדק ברשת ומתי", עם קישור
   אמיתי לכל מקור והכתובת גם כטקסט, להדפסה.
7. **נספח: ציטוטים מילוליים.**

**סימון החיסיון** ("טיוטה, טעונה אישור" והסימון של עורך הדין) בכותרת העליונה
ובכותרת התחתונה של כל עמוד, באותו נוסח כמו בדוח. הקובץ נשמר בתיקיית העסקה,
לצד המרשם, ושמו כולל את התאריך; קובץ קיים אינו נדרס.

    python "AREO_RT/skills/contract-risk-assessor/scripts/build_risk_docx.py" --data "<תיקיית העסקה>/risk-register.json"

**שפה** (דרישת מוצר: deliverable_language קובע את שפת התוצרים): `--lang he|en`, ובלעדיו `deliverable_language`
מ-`--profile` (`both`: `display_language` שבפרופיל), ובלעדיו `meta.display_language` שבמרשם. בעברית: RTL מלא, כמו תמיד. באנגלית: כל כותרת, תווית,
עמודה, סימון החיסיון ושם הקובץ באנגלית, והמסמך LTR מלא (בלי bidi ובלי rtl, יישור לשמאל), באותו נוסח כמו הדוח.
נוסח מצוטט נשאר בשפת המקור.

קוד יציאה: **0** נבנה, **2** קלט חסר, **3** בדיקת הכיווניות נכשלה.
"""
import argparse
import datetime as _dt
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # גם ב-python -I, שאינו מוסיף את תיקיית הסקריפט
import areo_lib  # noqa: F401  מוסיף את areolegal/lib לנתיב הייבוא

from docx import Document  # noqa: E402
from docx.opc.constants import RELATIONSHIP_TYPE as RT  # noqa: E402
from docx.oxml import OxmlElement  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402
from docx.shared import Pt, RGBColor  # noqa: E402

from common import paths, rtl  # noqa: E402
import risk_states as RS  # noqa: E402  שלושה מצבים לכל סיכון
from risk.render_check import band_text_from_register  # noqa: E402

LENS_HE = {"legal": "משפטי-חוזי", "financial": "כספי", "operational": "תפעולי", "technology": "טכנולוגי וסייבר",
           "regulatory": "רגולציה ופרטיות", "reputational": "מוניטין", "insurance": "ביטוח",
           "force_majeure": "כוח עליון וגיאופוליטי"}
LEVEL_HE = {"critical": "קריטי", "high": "גבוה", "medium": "בינוני", "low": "נמוך"}
LEVEL_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SIGN_HE = {"yes": "אפשר לחתום כמו שהוא", "with_fixes": "אפשר לחתום אחרי התיקונים", "no": "לא מומלץ לחתום כמו שהוא"}
SIDE_HE = {"as_obligor": "כמי שמתחייב", "as_beneficiary": "כמי שהסעיף מגן עליו", "both": "בשני התפקידים",
           "as_discloser": "כמי שהסעיף מגן עליו", "as_recipient": "כמי שמתחייב"}
STATUS_HE = {"findings": "נמצאו ממצאים", "none_found": "נבדק ולא נמצא", "not_checked": "לא נבדק"}

# תוצר באנגלית (deliverable_language קובע את שפת התוצר). אותו נוסח כמו EN בתבנית ה-HTML.
LENS_EN = {"legal": "Legal and contractual", "financial": "Financial", "operational": "Operational",
           "technology": "Technology and cyber", "regulatory": "Regulation and privacy", "reputational": "Reputation",
           "insurance": "Insurance", "force_majeure": "Force majeure and geopolitical"}
LEVEL_EN = {"critical": "Critical", "high": "High", "medium": "Medium", "low": "Low"}
SIGN_EN = {"yes": "Can be signed as is", "with_fixes": "Can be signed after the fixes",
           "no": "Should not be signed as is"}
SIDE_EN = {"as_obligor": "As the bound party", "as_beneficiary": "As the protected party", "both": "In both roles",
           "as_discloser": "As the protected party", "as_recipient": "As the bound party"}
STATUS_EN = {"findings": "Findings identified", "none_found": "Checked, nothing found", "not_checked": "Not checked"}

T = {
    "he": {"lens": LENS_HE, "level": LEVEL_HE, "sign": SIGN_HE, "side": SIDE_HE, "status": STATUS_HE,
           "title": "Areo Workspace | סיכונים", "glance": "התמונה במבט אחד",
           "head": ("הצד שכנגד", "העסקה", "הצד שלנו בהסכם", "מה נסרק", "מה לא נמסר", "מה שביקשתם לבדוק, בלשונכם"),
           "bl": "השורה התחתונה",
           "lenses": "העדשות", "lens_head": ("עדשה", "מצב", "סיכונים"),
           "counts": "סיכונים: %d   סתירות: %d   צירופים: %d", "dates": "מועדים קריטיים",
           "dates_head": ("מתי", "מה קורה", "סעיף", "מה אם חולף"), "no_entity": "עוד לא בדקנו את הצד השני במרשמים הרשמיים.",
           "ch1": "1. הסיכונים", "ch1_head": ("מספר", "עדשה", "הסיכון בשורה אחת", "סעיף", "חומרה", "כיוון טיפול"),
           "ch2": "2. סתירות בין ההסכם לנספחים", "ch2_head": ("נושא", "למה מסוכן", "מה גובר", "התיקון"),
           "no_defects": "לא נמצאו סתירות.", "ch3": "3. צירופים ושרשראות",
           "breaking": "התיקון ששובר את הצירוף: %s", "no_combos": "לא נמצאו צירופים.",
           "ch4": "4. הסיכונים הקריטיים בפירוט", "no_crit": "לא דורג סיכון קריטי.",
           "ch5": "5. מה לא נבדק ומה חסר", "assume": "הנחה לאישור: %s", "web": "מה נבדק ברשת ומתי", "web_doc": "מקורות רגולטוריים ממחקר הפלייבוק ומהמסמכים (לא נפתחו ברשת בהרצה הזו)",
           "open": "פתיחה", "dd": "הבדיקה אינה תחליף לבדיקת נאותות פיננסית מלאה.",
           "app": "נספח: ציטוטים מילוליים", "app_head": ("מספר", "מסמך וסעיף", "הנוסח המילולי"),
           "file": "%s - דוח סיכונים - %s.docx", "agreement": "הסכם", "mutual": "הדדי",
           "money": "התמונה הכספית", "money_head": ("החשיפה", "סכום או טווח", "המקור", "סיכונים"),
           "to": " עד ", "upto": "עד ", "unl": "בלתי מוגבל", "no_amt": "אין בהסכם או מהלקוח סכום",
           "src": {"contract": "מתוך ההסכם", "client": "לפי מסירת הלקוח"},
           "per": {"שנתי": "לשנה", "כולל": "בסך הכול", "annual": "לשנה", "total": "בסך הכול"},
           "dv": "שווי העסקה", "no_dv": "לא ידוע", "term": ", לתקופה של %s", "ins": "ביטוח", "req": "ההסכם מחייב",
           "held": "הכיסוי שבידינו",
           "no_req": "אין בהסכם סכום ביטוח", "no_held": "אין בתיק מסמך מהמבטח; ראו פרק 5", "old_ins": "ראו פרק 5",
           "no_money": "אין בהסכם או מהלקוח סכום לאף חשיפה.",
           "money_lg": "סכומים רק מההסכם או ממסירת הלקוח; טווח רק כשאין סכום מדויק. אין סכימה בין החשיפות, ואין "
                       "יחס מחושב.",
           "treated": "טופל"},
    "en": {"lens": LENS_EN, "level": LEVEL_EN, "sign": SIGN_EN, "side": SIDE_EN, "status": STATUS_EN,
           "title": "Areo Workspace | Risks", "glance": "At a glance",
           "head": ("Counterparty", "The deal", "Our side", "Reviewed", "Not provided",
                    "What you asked us to look at, in your words"),
           "bl": "Bottom line",
           "lenses": "The lenses", "lens_head": ("Lens", "Status", "Risks"),
           "counts": "Risks: %d   Conflicts: %d   Combinations: %d", "dates": "Critical dates",
           "dates_head": ("When", "What happens", "Clause", "If it passes"),
           "no_entity": "We haven't checked the other side in the official registers yet.",
           "ch1": "1. Risks", "ch1_head": ("#", "Lens", "The risk in one line", "Clause", "Severity",
                                          "Treatment direction"),
           "ch2": "2. Agreement vs annexes", "ch2_head": ("Topic", "Why it is dangerous", "What prevails", "The fix"),
           "no_defects": "No conflicts were found.", "ch3": "3. Combinations and chains",
           "breaking": "The one fix that breaks it: %s", "no_combos": "No combinations were found.",
           "ch4": "4. Critical risks in detail", "no_crit": "No risk was rated critical.",
           "ch5": "5. Not checked and missing", "assume": "Assumption to confirm: %s",
           "web": "What was checked online, and when",
           "web_doc": "Regulatory sources from the playbook research and the documents (not opened online in this run)",
           "open": "Open",
           "dd": "This check is not a substitute for full financial due diligence.",
           "app": "Appendix: verbatim quotes", "app_head": ("#", "Document and clause", "Verbatim text"),
           "file": "%s - Risk report - %s.docx", "agreement": "Agreement", "mutual": "mutual",
           "money": "The money picture", "money_head": ("Exposure", "Amount or range", "Source", "Risks"),
           "to": " to ", "upto": "up to ", "unl": "unlimited",
           "no_amt": "No amount in the agreement or from the client",
           "src": {"contract": "from the agreement", "client": "as provided by the client"},
           "per": {"שנתי": "per year", "כולל": "in total", "annual": "per year", "total": "in total"},
           "dv": "Deal value", "no_dv": "Not known", "term": ", term: %s", "ins": "Insurance",
           "req": "The agreement requires", "held": "Our cover", "no_req": "No insurance amount in the agreement",
           "no_held": "No insurer document in the file; see chapter 5", "old_ins": "See chapter 5",
           "no_money": "No amount in the agreement or from the client for any exposure.",
           "money_lg": "Amounts only from the agreement or from the client; a range only without an exact amount. "
                       "Not added up, and not a ratio.",
           "treated": "Treated in the document"},
}


def report_lang(reg, lang=None, profile=None):
    """--lang, אחריו deliverable_language בפרופיל, אחריו display_language שבמרשם; he או en.
    deliverable_language "both": התוצר הראשי בשפת הממשק, display_language שבפרופיל (language-policy.md)."""
    prof = profile or {}
    dl = prof.get("deliverable_language")
    if str(dl or "").strip().lower() == "both":
        dl = prof.get("display_language")
    return rtl.lang_of(lang, dl, (reg.get("meta") or {}).get("display_language"))


def load(path):
    if not os.path.exists(path):
        print("המרשם אינו קיים: %s" % path)
        raise SystemExit(2)
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


def h(doc, text, size=14):
    p = rtl.add_paragraph(doc, text, bold=True, size=size)
    return p


def para(doc, text, size=10.5, bold=False):
    return rtl.add_paragraph(doc, str(text or ""), bold=bold, size=size)


def table(doc, head, rows):
    t = doc.add_table(rows=1, cols=len(head))
    t.style = "Table Grid"
    for i, x in enumerate(head):
        c = t.rows[0].cells[i]
        c.text = x
        for r in c.paragraphs[0].runs:
            r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v if v is not None else "")
    rtl.set_table_rtl(t)
    return t


def hyperlink(paragraph, url, text):
    """קישור אמיתי (w:hyperlink עם יחס חיצוני), והכתובת עצמה גם כטקסט, כדי שתודפס."""
    part = paragraph.part
    rid = part.relate_to(url, RT.HYPERLINK, is_external=True)
    link = OxmlElement("w:hyperlink")
    link.set(qn("r:id"), rid)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    color = OxmlElement("w:color")
    color.set(qn("w:val"), "0563C1")
    rpr.append(color)
    u = OxmlElement("w:u")
    u.set(qn("w:val"), "single")
    rpr.append(u)
    run.append(rpr)
    t = OxmlElement("w:t")
    t.text = text
    t.set(qn("xml:space"), "preserve")
    run.append(t)
    link.append(run)
    paragraph._p.append(link)
    tail = paragraph.add_run(" (%s)" % url)
    tail.font.size = Pt(8)
    rtl.set_run_ltr(tail)
    return paragraph


def band(doc, text):
    for sec in doc.sections:
        for part in (sec.header, sec.footer):
            p = part.paragraphs[0] if part.paragraphs else part.add_paragraph()
            r = p.add_run(text)
            r.font.size = Pt(8)
            r.font.color.rgb = RGBColor(0x9A, 0x34, 0x12)


def quotes_index(reg):
    """כל ציטוט מקבל מספר אחד בנספח, וכל הפניה בדוח היא למספר הזה."""
    seen, out = {}, []
    def add(a):
        if not a or not a.get("quote"):
            return None
        key = (a.get("document"), a.get("clause"), a.get("quote"))
        if key not in seen:
            seen[key] = len(out) + 1
            out.append(a)
        return seen[key]
    for r in reg.get("risks") or []:
        r["_q"] = [add(a) for a in r.get("anchors") or []]
    for d in reg.get("document_defects") or []:
        d["_q"] = [add(a) for a in d.get("locations") or []]
    for c in reg.get("dangerous_combinations") or []:
        c["_q"] = [add(a) for a in c.get("anchors") or []]
    return out


def refs(nums):
    return " ".join("[%d]" % n for n in nums or [] if n)


# המטבע כפי שנכתב במרשם: קוד ISO 4217, סימן או שם בעברית. אין ברירת מחדל: בלי מטבע, "[להשלים]"
CUR_WORDS = {"he": {"ILS": 'ש"ח', "USD": "דולר", "EUR": "אירו", "GBP": 'ליש"ט', "CHF": "פרנק שווייצרי",
                    "JPY": "ין יפני", "SGD": "דולר סינגפורי", "AED": "דירהם", "CAD": "דולר קנדי",
                    "AUD": "דולר אוסטרלי", "HKD": "דולר הונג קונגי", "CNY": "יואן", "INR": "רופי הודי",
                    "SEK": "כתר שוודי", "NOK": "כתר נורווגי", "DKK": "כתר דני", "PLN": "זלוטי",
                    "TRY": "לירה טורקית", "BRL": "ריאל ברזילאי", "NZD": "דולר ניו זילנדי"},
             "en": {"ILS": "NIS"}}
CUR_ALIASES = {"₪": "ILS", "NIS": "ILS", 'ש"ח': "ILS", "ש״ח": "ILS", "שקל": "ILS", "שקלים": "ILS",
               "$": "USD", "US$": "USD", "דולר": "USD", "דולרים": "USD", "€": "EUR", "אירו": "EUR", "יורו": "EUR",
               "£": "GBP", 'ליש"ט': "GBP", "ליש״ט": "GBP", "לירה שטרלינג": "GBP", "לירות שטרלינג": "GBP",
               "פרנק": "CHF", "פרנקים": "CHF", "FR.": "CHF", "¥": "JPY", "ין": "JPY", "S$": "SGD", "A$": "AUD",
               "C$": "CAD", "HK$": "HKD", "דירהם": "AED"}
TO_COMPLETE = {"he": "[להשלים]", "en": "[to complete]"}


def currency_label(cur, lang):
    """המטבע במילים בשפת התוצר. קוד או סימן שאינו מוכר מוצג כפי שנכתב; בלי מטבע, "[להשלים]"."""
    lang = "en" if lang == "en" else "he"
    raw = str(cur or "").strip()
    if not raw:
        return TO_COMPLETE[lang]
    code = CUR_ALIASES.get(raw) or CUR_ALIASES.get(raw.upper()) or raw.upper()
    return CUR_WORDS[lang].get(code) or (code if len(code) == 3 and code.isalpha() and code.isascii() else raw)


MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December")


def fmt_date(v, lang):
    """תאריך לתצוגה (כלל 3.6): D.M.YYYY בעברית, "3 April 2027" באנגלית. ערך שאינו ISO מוצג כפי שהוא."""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(v or ""))
    if not m:
        return v or ""
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return "%d %s %d" % (d, MONTHS_EN[mo - 1], y) if lang == "en" else "%d.%d.%d" % (d, mo, y)


def money(a, lang):
    """סכום עם המטבע במילים, כמו money() בתבנית. אין מטבע ברירת מחדל: מטבע חסר הוא "[להשלים]"."""
    if not a or a.get("value") is None:
        return ""
    v = float(a["value"])
    num = format(int(v), ",") if v == int(v) else format(v, ",.2f")
    return num + " " + currency_label(a.get("currency"), lang)


def money_rows(reg, L, lang):
    """התמונה הכספית, באותו נוסח כמו בתבנית: עד שלוש חשיפות, ושורות שווי העסקה והביטוח.
    מרשם ישן בלי summary.money_picture: הסכומים שבסיכונים עצמם."""
    s, m = reg.get("summary") or {}, reg.get("meta") or {}
    mp = s.get("money_picture")

    def src(a):
        return (L["src"][a["source"]] + (", " + a["source_ref"] if a.get("source_ref") else "")) \
            if a and a.get("source") in L["src"] else ""

    def calc(a):
        return [a["calc"]] if a and a.get("calc") and a["calc"] != "כלשון הסעיף" else []

    nos = {r.get("id"): r.get("risk_no") for r in reg.get("risks") or []}
    rows = []
    if mp and mp.get("exposures"):
        for x in mp["exposures"]:
            am, rg = x.get("amount") or {}, x.get("range") or {}
            lo, hi = rg.get("low") or {}, rg.get("high") or {}
            if am.get("value") is not None:
                v, sr, c = money(am, lang), src(am), calc(am)
            elif lo.get("value") is not None or hi.get("value") is not None or rg.get("high_unlimited"):
                top = L["unl"] if rg.get("high_unlimited") else money(hi, lang)
                v = (money(lo, lang) + (L["to"] + top if top else "")) if lo.get("value") is not None \
                    else (L["unl"] if rg.get("high_unlimited") else L["upto"] + top)
                sr, c = "; ".join(x for x in (src(lo), src(hi)) if x), calc(lo) + calc(hi)
            else:
                v, sr, c = L["no_amt"], x.get("reason") or "", []
            rows.append((x.get("what") or "", v + (" (%s)" % "; ".join(c) if c else ""), sr,
                         ", ".join(str(n) for n in sorted(nos.get(i) for i in x.get("risk_ids") or [] if nos.get(i)))))
    else:
        rs = [r for r in reg.get("risks") or []
              if ((r.get("exposure") or {}).get("amount") or {}).get("value") is not None]
        for r in sorted(rs, key=lambda r: -float(r["exposure"]["amount"]["value"])):
            a = r["exposure"]["amount"]
            rows.append((r.get("name") or "", money(a, lang) + (" (%s)" % "; ".join(calc(a)) if calc(a) else ""),
                         src(a), str(r.get("risk_no") or "")))
    dv = m.get("deal_value") or {}
    dv_txt = (money({"value": dv["amount"], "currency": dv.get("currency")}, lang)
              + (" " + L["per"][dv.get("basis")] if L["per"].get(dv.get("basis")) else "")
              + (L["term"] % dv["term"] if dv.get("term") else "")
              + (" (%s)" % src(dv) if src(dv) else "")) if dv.get("amount") is not None else L["no_dv"]
    if mp:
        ins = mp.get("insurance") or {}

        def one(a, empty):
            a = a or {}
            return money(a, lang) + (" (%s)" % src(a) if src(a) else "") if a.get("value") is not None \
                else (a.get("text") or empty)
        ins_txt = "%s: %s · %s: %s" % (L["req"], one(ins.get("required"), L["no_req"]),
                                       L["held"], one(ins.get("held"), L["no_held"]))
    else:
        ins_txt = L["old_ins"]
    return rows, "%s: %s" % (L["dv"], dv_txt), "%s: %s" % (L["ins"], ins_txt)


def critical_text(r):
    """critical_detail הוא אובייקט (what_happens, why_not_protected) בסכמה; טקסט חופשי נשאר כמו שהוא."""
    cd = r.get("critical_detail")
    if isinstance(cd, dict):
        return " ".join(x for x in (cd.get("what_happens"), cd.get("why_not_protected")) if x)
    return cd or r.get("description")


def build(reg, out, lang="he"):
    RS.derive_levels(reg)
    L = T["en" if lang == "en" else "he"]
    m, s = reg.get("meta") or {}, reg.get("summary") or {}
    quotes = quotes_index(reg)
    risks = sorted(reg.get("risks") or [], key=lambda r: (LEVEL_ORDER.get(r.get("severity_level"), 9),
                                                          r.get("risk_no") or 0))
    pos = str(m.get("position") or "")
    mutual = "הדדי" in pos or "mutual" in pos.lower() or m.get("mutual_primary_role")
    doc = Document()
    band(doc, band_text_from_register(reg, lang))

    h(doc, L["title"], 16)
    h(doc, m.get("scope_label") or "", 13)
    h(doc, L["glance"])
    cp = (m.get("counterparty") or {}).get("name") if isinstance(m.get("counterparty"), dict) else m.get("counterparty")
    vals = (cp, s.get("deal_one_line"), m.get("position"),
            ", ".join(m.get("annexes_reviewed") or []) if isinstance(m.get("annexes_reviewed"),
                                                                    list) else m.get("annexes_reviewed"),
            ", ".join(m.get("annexes_missing") or []) if isinstance(m.get("annexes_missing"),
                                                                   list) else m.get("annexes_missing"),
            # דברי המשתמש כלשונם, כציטוט
            '"%s"' % m["user_focus"] if m.get("user_focus") else None)
    for label, val in zip(L["head"], vals):
        if val:
            para(doc, "%s: %s" % (label, val))
    h(doc, L["bl"], 12)
    for line in s.get("bottom_line") or []:
        para(doc, line)
    if s.get("sign_as_is"):
        para(doc, L["sign"].get(s["sign_as_is"], s["sign_as_is"]), bold=True)
    # התמונה הכספית, באותו מקום ובאותו נוסח כמו בדוח
    h(doc, L["money"], 12)
    mrows, dv_line, ins_line = money_rows(reg, L, lang)
    if mrows:
        table(doc, L["money_head"], mrows)
    else:
        para(doc, L["no_money"])
    para(doc, dv_line)
    para(doc, ins_line)
    para(doc, L["money_lg"], size=9)
    h(doc, L["lenses"], 12)
    table(doc, L["lens_head"], [(L["lens"].get(c.get("lens"), c.get("lens")),
                                 L["status"].get(c.get("status"), c.get("status")),
                                 len(c.get("risk_ids") or [])) for c in reg.get("coverage") or []])
    para(doc, L["counts"] % (len(risks), len(reg.get("document_defects") or []),
                             len(reg.get("dangerous_combinations") or [])), bold=True)
    if s.get("key_dates"):
        h(doc, L["dates"], 12)
        table(doc, L["dates_head"],
              [(fmt_date(k.get("date"), lang) or k.get("window"), k.get("what"), k.get("clause"), k.get("consequence"))
               for k in s["key_dates"][:5]])
    er = reg.get("entity_research") or {}
    para(doc, er.get("note") or (L["no_entity"] if er.get("status") != "done" else ""))

    h(doc, L["ch1"])
    rows = []
    for r in risks:
        name = r.get("name") or ""
        if mutual and r.get("side"):
            name = "%s: %s" % (L["side"].get(r["side"], r["side"]), name)
        a = (r.get("anchors") or [{}])[0]
        clause = a.get("clause") or ""
        if len(set(r.get("concession_refs") or [])) > 1:
            # ויתורים מאוחדים (concession_refs): כל הסעיפים בשורה אחת, כמו בדוח
            clause = "; ".join(dict.fromkeys(x.get("clause") for x in r.get("anchors") or [] if x.get("clause")))
        rows.append((r.get("risk_no"), L["lens"].get(r.get("primary_lens"), r.get("primary_lens")), name,
                     "%s %s" % (clause, refs(r.get("_q"))),
                     L["level"].get(r.get("severity_level"), "") + (
                         " · " + L["treated"] if (r.get("residual") or {}).get("treated") else "") + (
                         " · " + RS.STATE_LABEL_EN.get(r.get("exposure_state"), "") if lang == "en" and r.get("exposure_state") in ("proposed", "agreed")
                         else " · " + RS.STATE_LABEL.get(r.get("exposure_state"), "") if r.get("exposure_state") in ("proposed", "agreed") else ""),
                     r.get("treatment_direction")))
    table(doc, L["ch1_head"], rows)

    h(doc, L["ch2"])
    defects = reg.get("document_defects") or []
    if defects:
        table(doc, L["ch2_head"],
              [(d.get("topic") or d.get("title"), "%s %s" % (d.get("risk_created") or "", refs(d.get("_q"))),
                d.get("prevails") or d.get("what_prevails") or "", d.get("fix") or d.get("proposed_fix") or "")
               for d in defects])
    else:
        para(doc, L["no_defects"])

    h(doc, L["ch3"])
    combos = reg.get("dangerous_combinations") or []
    for c in combos:
        para(doc, "%s %s" % (c.get("why_together") or "", refs(c.get("_q"))))
        if c.get("breaking_fix"):
            para(doc, L["breaking"] % c["breaking_fix"], size=10)
    if not combos:
        para(doc, L["no_combos"])

    h(doc, L["ch4"])
    crit = [r for r in risks if r.get("severity_level") == "critical"]
    for r in crit:
        para(doc, "%s. %s" % (r.get("risk_no"), r.get("name")), bold=True)
        para(doc, critical_text(r))
    if not crit:
        para(doc, L["no_crit"])

    h(doc, L["ch5"])
    for x in s.get("not_checked") or []:
        para(doc, "%s: %s (%s)" % (x.get("item"), x.get("why"), x.get("who")) if isinstance(x, dict) else x)
    for x in s.get("assumptions") or []:
        para(doc, L["assume"] % ((x.get("text") or x.get("assumption") or "") if isinstance(x, dict) else x))
    src = (reg.get("research") or {}).get("sources_checked") or []
    if src:
        # אין אימות רגולטורי ברשת: רק מרשם ישן (approved_sources) מציג "מה נבדק ברשת"
        h(doc, L["web"] if (reg.get("research") or {}).get("mode") == "approved_sources" else L["web_doc"], 12)
        for n, x in enumerate(src, 1):
            p = para(doc, "%d. %s: %s. " % (n, x.get("source"), x.get("taken") or x.get("subject") or ""), size=10)
            if x.get("url"):
                hyperlink(p, x["url"], L["open"])
            p.add_run(" %s" % fmt_date(x.get("date"), lang))
        para(doc, L["dd"], size=9)

    h(doc, L["app"])
    table(doc, L["app_head"],
          [(n, "%s, %s" % (a.get("document"), a.get("clause")), a.get("quote")) for n, a in enumerate(quotes, 1)])
    # עברית: RTL מלא (bidi, rtl, bidiVisual, rtlGutter); אנגלית: LTR מלא, יישור לשמאל, בלי סימוני RTL
    rtl.enforce(doc, lang, author=m.get("prepared_for_counsel") or "")
    doc.save(out)


def main(argv=None):
    sys.dont_write_bytecode = True
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--data", required=True, help="risk-register.json, בתיקיית העסקה")
    ap.add_argument("--date", help="DD.MM.YYYY; בלעדיו: היום")
    ap.add_argument("--lang", choices=("he", "en"), help="שפת ה-Word; בלעדיו: deliverable_language בפרופיל, "
                                                         "ואחריו meta.display_language שבמרשם")
    ap.add_argument("--profile", help="פרופיל-לקוח.json: שפת התוצר (deliverable_language)")
    a = ap.parse_args(argv)
    reg = load(a.data)
    prof = load(a.profile) if a.profile else {}
    lang = report_lang(reg, a.lang, prof)
    L = T[lang]
    date = a.date or _dt.date.today().strftime("%d.%m.%Y")
    label = re.sub(r'[\\/:*?"<>|]', "", re.sub(r",\s*\d{2}\.\d{2}\.\d{4}$", "",
                                                (reg.get("meta") or {}).get("scope_label") or L["agreement"]))
    out = paths.unique_path(os.path.join(os.path.dirname(os.path.abspath(a.data)), L["file"] % (label, date)))
    paths.check_write_path(out)
    build(reg, out, lang)
    problems = rtl.audit(out, lang, run_date=_dt.date.today())
    print("נבנה: %s" % out)
    for p in problems:
        print("  בדיקת כיווניות: %s" % p)
    return 3 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
