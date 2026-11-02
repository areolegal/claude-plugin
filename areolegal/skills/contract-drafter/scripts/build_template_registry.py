# -*- coding: utf-8 -*-
"""סורק את תיקיות ההסכמים המחוברות ובונה את מרשם התבניות של הלקוח.

שימוש:
  python3 build_template_registry.py --folders "<תיקייה>" ["<תיקייה נוספת>" ...] \
      --out "Areo-נתונים/template-registry.json" [--playbook "Areo-נתונים/playbooks/<family_id>/playbook-model.json"] \
      [--role receiving] --profile "<profile_path של הישות>" [--approved "<קובץ>" ...]

--playbook: הקובץ של הרשומה המתאימה ב-Areo-נתונים/playbooks/index.json.

הסקריפט מסווג כל מסמך ומחשב, לכל צירוף של משפחה, תפקיד, שפה והדדיות, מי התבנית המאושרת הנוכחית.
התפקיד נלקח מהארגומנט --role (מה שמסר המשתמש), אחרת מ-company_role_code של הפלייבוק לאותה משפחה, ורק
בלעדיהם מספירת מילים בגוף, ואז הוא מסומן "טעון אישור" (company_role_basis).
הוא אינו ממציא סיווג: מסמך שאינו ניתן לסיווג חד-משמעי נכנס לתור בדיקה עם ציון הסיבה.

**תבנית מאושרת (approved_current) רק על נייר החברה, או באישור המשתמש.** שדות ריקים מעידים שזה טופס, לא
שזה הטופס של החברה: טופס של גוף ציבורי, של לקוח או של הליך תחרותי מלא קווים ריקים בדיוק כמו תבנית של החברה. לכן
מסמך נבחר רק כששם החברה (organization_name או organization_name_en בפרופיל, --company) או מספר הרישום שלה מופיע בבלוק הצדדים, או
כשהמשתמש אישר אותו (--approved). בלי --profile ובלי --company אין בדיקה, ולכן אין תבנית מאושרת כלל.
טופס שהצד הריק בפתיח שלו הוא הצד של החברה, או נוסח של הליך תחרותי כשהחברה אינה הגוף המזמין, הוא טופס של הצד שכנגד
(paper_owner), ואינו נבחר גם כששם החברה בבלוק הצדדים, אלא באישור המשתמש. אותם סימנים כמו בבונה הפלייבוק.
PDF נקרא ונרשם (סיווג, משפחה, נייר), אבל לעולם אינו נבחר כתבנית: הצרכנים במורד הזרם קוראים docx.

זיהוי הסיווג נשען על סימנים בטקסט ובמבנה הקובץ בלבד. הוא כלי עזר לרכיב, לא תחליף לשיקול דעת:
הרכיב מציג את המרשם למשתמש ומבקש אישור לפני שהוא מסתמך עליו.
"""
import argparse, hashlib, io, json, os, re, sys, zipfile
from datetime import datetime

try:                                   # פלט עברי במסוף של Windows (cp1255) נשבר בלי זה
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):   # pragma: no cover
    pass

# ---- הגנה על קובצי הקלט: אותו כלל כמו common.cli.guard_out בספרייה המשותפת, שהמנסח אינו מוסיף לנתיב.
# כל סקריפט של המנסח שכותב --out (או --cover, --json, --out-dir) קורא לה לפני הכתיבה
PROTECTED_EXT = (".docx", ".doc", ".docm", ".dotx", ".pdf", ".xlsx", ".pptx")


def _path_key(p):
    return os.path.normcase(os.path.realpath(os.path.abspath(p)))


def out_problem(out, inputs=(), force=False):
    """None כשמותר לכתוב, אחרת הסיבה. הפלט לעולם אינו אחד מקובצי הקלט, ואינו מסמך קיים (docx, pdf, xlsx
    וכו') בלי --force: הרצה חוזרת על טיוטה קיימת היא החלטה מפורשת, לא ברירת מחדל."""
    if not out or not str(out).strip():
        return "חסר נתיב פלט"
    k = _path_key(out)
    for p in inputs or ():
        if p and _path_key(p) == k:
            return "נתיב הפלט הוא קובץ קלט (%s). פלט לעולם אינו נכתב על קובץ קלט" % p
    if not force and os.path.isfile(k) and os.path.splitext(k)[1].lower() in PROTECTED_EXT:
        return "נתיב הפלט הוא מסמך קיים (%s). לדריסה מכוונת, הוסיפו --force" % out
    return None


def guard_out(out, inputs=(), force=False):
    """עוצר בקוד יציאה 2, לפני כל כתיבה, כשנתיב הפלט אסור (out_problem)."""
    problem = out_problem(out, inputs, force)
    if problem:
        print("הפלט לא נכתב: " + problem)
        sys.exit(2)
    return out

# ציין החוסר האחיד בשתי השפות (areo-hard-rules 3.5): "[להשלים]" ו-"[to complete]", בכל רישיות, גם עם פירוט
PLACEHOLDER = re.compile(r"\[\s*להשלים\s*(?::[^\]\n]{0,120})?\]|\[\s*(?i:to\s+complete)\s*(?::[^\]\n]{0,120})?\]|"
                         r"_{4,}|\bXXX+\b|\[\s{2,}\]|\[●\]|\[\*+\]")
# בלוק חתימה. אותו ביטוי בדיוק כמו SIGNED ב-`build_corpus_manifest.py` של בונה הפלייבוק, כדי ששני
# הרכיבים יסווגו אותו מסמך באותה דרך; שינוי כאן נעשה גם שם. "Signed by" ו-"Executed by" רק
# בתחילת שורה, כי "deemed executed by the parties" בגוף ההסכם אינו בלוק חתימה; ו-/s/ לא
# בתוך כתובת אתר
SIGN_DATE = re.compile(
    r"IN\s+WITNESS\s+WHEREOF"
    r"|ולראי{1,2}ה\s+(?:באו|באנו|חתמו|חתמנו)|ובאו\s+הצדדים\s+על\s+החתום|חתימת\s+הצדדים"
    r"|(?m:^)[ \t]*(?-i:Signed|SIGNED|Executed|EXECUTED)\s+(?:by|for\s+and\s+on\s+behalf)\b"
    r"|\b(?:have|has)\s+(?:duly\s+)?executed\s+this\b|(?<![\w/])/s/"
    r"|signature\s+of\s+the\s+parties"
    r"|(?:נחתם|תאריך\s+החתימה|Signed\s+on|Date\s+of\s+signature)\s*[:\-]?\s*\d", re.I)
# קו חתימה בסוף המסמך אינו שדה למילוי אלא המקום לחתום בו, ולכן אינו נספר בתוך 300 התווים
# האחרונים. כך גם בבונה הפלייבוק
LINE_RUN = re.compile(r"_{4,}|\.{6,}")
SIGN_TAIL = 300
# תבנית של צד שכנגד, אותם סימנים כמו ב-`build_corpus_manifest.py` של בונה הפלייבוק (BLANK_PARTY, PROCEDURE_SIGN),
# בכל סוג הסכם: חוזה של צד אחד, תנאים כלליים של צד, טופס שצד מפרסם, נספח להליך תחרותי.
#   1. הסימן הכללי: הצד שפרטיו ריקים בפתיח ("________ (להלן: "<תפקיד>")") הוא הצד שהחברה ממלאת. בתבנית של החברה
#      ריקים פרטי הצד שכנגד; בטופס של הצד שכנגד, פרטי החברה. נבדק רק כשהתפקיד של החברה ידוע (--role או פלייבוק).
#   2. נוסח של הליך תחרותי, כשהחברה אינה הגוף המזמין. הסימן הכללי גובר עליו.
BLANK_PARTY = re.compile(r'(?:_{4,}|\.{6,}|\[[^\]]{0,40}\]|<<[^>]{1,40}>>|\{\{[^}]{1,40}\}\})[^"״“()\n]{0,60}[()]\s*'
                         r'(?:להלן\s*[:\-]?\s*|hereinafter(?:\s+(?:referred\s+to\s+as|called))?\s*[:,]?\s*(?:the\s+)?'
                         r'|the\s+)?["״“]([^"״”()]{2,40})["״”]', re.I)
PROCEDURE_SIGN = re.compile(r"המציע|הליך תחרותי|\bcompetitive\s+procedure\b|\bbidders?\b|\bRFP\b|request\s+for\s+proposals?"
                         r"|invitation\s+to\s+(?:bid|tender)", re.I)


def placeholder_count(text):
    """שדות למילוי, בלי קווי חתימה ב-300 התווים האחרונים."""
    cut = len(text) - SIGN_TAIL
    return sum(1 for m in PLACEHOLDER.finditer(text)
               if not (m.start() >= cut and LINE_RUN.fullmatch(m.group(0))))

# שער מקדים: האם המסמך הוא בכלל מסמך חוזי. בתיקייה של לקוח אמיתי יש נהלים,
# מדריכים, הצעות מחיר ומצגות, ואסור שייכנסו למרשם התבניות.
# רשימות נפרדות לכל שפה. רשימה מעורבת עם רוב עברי מכשילה כל הסכם אנגלי:
# מסמך אנגלי יכול לצבור לכל היותר את מספר הסימנים האנגליים, והסף אינו מודע לכך.
MARKERS_HE = ["בין", "לבין", "הצדדים", "הואיל", "מוסכם", "התחייבות", "סעיף",
              "בתוקף", "תקופת ההסכם", "הפרה", "שיפוי", "סודיות", "ולראיה",
              "נספח", "הודעה מוקדמת", "אחריות", "תמורה"]
MARKERS_EN = ["whereas", "the parties", "agreement", "hereby", "shall", "termination",
              "in witness", "governing law", "confidential", "indemnif", "liability",
              "warrant", "herein", "thereof", "effective date", "exhibit", "schedule",
              "written notice", "breach", "assignment", "entire agreement", "force majeure"]
NON_CONTRACT_TITLES = re.compile(
    r"נוהל|מדריך|הצעת\s*מחיר|מצגת|סיכום\s*פגישה|פרוטוקול|דוח|טיוטת\s*מייל|readme|"
    r"פלייבוק|playbook|מערכת\s*התרעות|מתווה|לוח\s*מועדים|דשבורד|workspace|"
    r"guide|manual|proposal|quote|presentation|minutes|report|skill", re.I)

# שם קובץ שיש בו מילת הסכם, בכל מקום בשם ולא רק בפתיחה. "Reseller Agr." ו-
# שמות כמו "Final" הם שמות אמיתיים של הסכמים, והדרישה שהשם ייפתח במילה חסמה אותם.
CONTRACT_TITLE = re.compile(
    r"הסכם|חוזה|תוספת|נספח|agreement|contract|addendum|amendment|"
    r"\bagr\b|\bmou\b|\bloi\b|license", re.I)

def is_contract(text, name, ext):
    """מחזיר (האם חוזי, סיבה). שמרני בכוונה: עדיף להוציא לתור בדיקה מאשר לזהם את המרשם."""
    if ext in (".md",):
        return False, "קובץ Markdown, אינו מסמך חוזי"
    if NON_CONTRACT_TITLES.search(name):
        return False, "שם הקובץ מעיד על מסמך שאינו חוזי"
    if len(text) < 1200:
        return False, "המסמך קצר מדי מכדי להיות הסכם"
    low = text.lower()
    he_hits = sum(1 for m in MARKERS_HE if m in low)
    en_hits = sum(1 for m in MARKERS_EN if m in low)
    # מודדים מול השפה שבה המסמך כתוב, ולא מול רשימה מעורבת
    if he_hits >= en_hits:
        hits, total, lang = he_hits, len(MARKERS_HE), "עברית"
    else:
        hits, total, lang = en_hits, len(MARKERS_EN), "אנגלית"
    named = bool(CONTRACT_TITLE.search(name))
    threshold = 3 if named else 5
    if hits < threshold:
        return False, "לא אותרו סימני מסמך חוזי ב%s (%d מתוך %d)" % (hits and lang or lang, hits, total)
    return True, ""
# תיקון מזוהה רק בשם הקובץ ובשורות הכותרת (שלוש הפסקאות הראשונות), ולא בגוף: "תיקון 13 לחוק",
# או "Data Processing Addendum to the Agreement", אינם תיקון להסכם. Addendum נחשב תיקון רק
# כשהוא פותח את הכותרת ("Addendum No. 2 to"); כשלפניו שם (Data Processing Addendum), זה שמו
# של הסכם עומד בפני עצמו. אותו ביטוי כמו AMENDMENT ב-`build_corpus_manifest.py`
AMEND = re.compile(r"תיקון\s*(?:מס(?:פר|['׳])?\.?\s*)?\d*\s*ל(?!חוק|תקנות|פקודת|פקודה|צו\b)"
                   r"|נספח\s+תיקון|תוספת\s+להסכם|הסכם\s+תיקון"
                   r"|\bamendment\s*(?:no\.?\s*\d+\s*)?to\b"
                   r"|^\s*(?:(?:first|second|third|\d+(?:st|nd|rd|th)?)\s+)?addendum\b"
                   r"\s*(?:(?:no\.?|number|#)\s*\d+\s*)?to\b", re.I)
HE = re.compile(r"[֐-׿]")
LAT = re.compile(r"[A-Za-z]")

# תפקידי הצדדים אינם רשימה בקוד. תפקיד החברה בא מהמשתמש (--role), מ-company_role_code של הפלייבוק, או נשאל
# ("תפקיד לא ידוע"). הוא טקסט חופשי, בלשון המסמכים של הלקוח; אין מילון תפקידים ואין זוגות "צד מול צד שכנגד".
# הצד שמזמין הצעות בהליך תחרותי (מבנה, לא סוג הסכם): ערך ש-company_role_code או --role נוקבים בו
ISSUER_WORDS = {"issuer", "contracting_authority", "inviting_party", "מזמין", "הגוף המזמין"}

# הסכם הדדי מול חד-צדדי: נוסח הדדי ונוסח חד-צדדי של אותה משפחה הם שתי תבניות שונות, ואסור שיתמזגו
# במפתח. נבדק רק בשם הקובץ ובשורות הכותרת, כי "mutual covenants" מופיע בפתיח של כל הסכם
MUTUAL = re.compile(r"(?<![\w֐-׿])(?:mutual|bilateral|reciprocal|הדדי|הדדית|דו[\s\-]?צדדי(?:ת)?)"
                    r"(?![\w֐-׿])(?!\s+(?:covenants|promises|obligations|consent|understanding))", re.I)
ONE_WAY = re.compile(r"(?<![\w֐-׿])(?:one[\s\-]way|unilateral|חד[\s\-]?צדדי(?:ת)?)(?![\w֐-׿])", re.I)


def _word_re(w, suffix):
    """מילה שלמה: מילה לטינית אינה נמצאת בתוך מילה ארוכה יותר. בעברית מותרות אותיות שימוש
    לפני המילה, וכש-suffix גם סיומת אחריה; לשם תפקיד לא."""
    lw = w.lower()
    if re.search(r"[a-z]", lw):
        pat = r"(?<![a-z0-9])" + re.escape(lw) + r"(?![a-z0-9])"
    else:
        pat = r"(?<![֐-׿])[ובלמהשכ]{0,2}" + re.escape(lw) + ("" if suffix else r"(?![֐-׿])")
    return re.compile(pat)


_WORD_CACHE = {}


def word_count(w, low, suffix=True):
    """כמה פעמים w מופיע כמילה שלמה בטקסט low (באותיות קטנות)."""
    if (w, suffix) not in _WORD_CACHE:
        _WORD_CACHE[(w, suffix)] = _word_re(w, suffix)
    return len(_WORD_CACHE[(w, suffix)].findall(low))


# אין כאן רשימת משפחות (סוגי הסכם). המשפחה נגזרת בזמן ריצה משם הקובץ ומהכותרת של המסמך של הלקוח עצמו
# (derive_family_name), מוצגת כהצעה, ואינה נקבעת בלי אישור המשתמש. מסמך שאין לו שם או כותרת מתאימים:
# "לא סווג", ושואלים.
FAMILIES = []


def docx_text(path, limit=200000):
    try:
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.startswith("word/") and n.endswith(".xml")]
            parts = []
            for n in ["word/document.xml"] + [x for x in names if x != "word/document.xml"]:
                if n not in z.namelist():
                    continue
                xml = z.read(n).decode("utf-8", "ignore")
                parts.append(xml)
                if sum(len(p) for p in parts) > limit * 3:
                    break
            xml = "".join(parts)
            has_tracked = ("<w:ins " in xml) or ("<w:del " in xml)
            has_comments = "word/comments.xml" in z.namelist()
            txt = re.sub(r"<[^>]+>", " ", xml)
            txt = re.sub(r"\s+", " ", txt)
            return txt[:limit], has_tracked, has_comments
    except Exception as e:
        return "", False, False

def docx_paragraphs(path, limit=4000, mode="final"):
    """מחזיר את פסקאות המסמך בנפרד, תוך שמירת גבולות הפסקה.

    mode:
      final  קבלת כל השינויים במעקב, כלומר הנוסח הנוכחי (ברירת מחדל)
      base   דחיית כל השינויים, כלומר הנוסח לפני שהצד שסימן נגע בו
      raw    הטקסט כפי שהוא, כולל הוספות ומחיקות מעורבבות

    docx_text משטח הכל לשורה אחת ולכן אינו מאפשר לזהות כותרות סעיף.
    במסמך redline, קריאה ב-raw מייצרת סעיפים משובשים שבהם הנוסח הישן
    והחדש משורגים, ולכן ברירת המחדל היא final ולא raw.
    """
    out = []
    try:
        with zipfile.ZipFile(path) as z:
            if "word/document.xml" not in z.namelist():
                return out
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
        for p in xml.split("</w:p>")[:limit]:
            if mode == "final":
                p = re.sub(r"<w:del\b[^>]*>.*?</w:del>", "", p, flags=re.S)
            elif mode == "base":
                p = re.sub(r"<w:ins\b[^>]*>.*?</w:ins>", "", p, flags=re.S)
                p = re.sub(r"<w:delText([^>]*)>", r"<w:t\1>", p)
                p = re.sub(r"</w:delText>", "</w:t>", p)
            t = re.sub(r"<[^>]+>", "", "".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", p, re.S)))
            t = re.sub(r"\s+", " ", t).strip()
            if t:
                out.append(t)
    except Exception:
        pass
    return out


def docx_num_formats(path):
    """פורמטי המספור האוטומטי של Word, כשהמספר אינו מופיע כטקסט בגוף המסמך."""
    try:
        with zipfile.ZipFile(path) as z:
            if "word/numbering.xml" not in z.namelist():
                return []
            xml = z.read("word/numbering.xml").decode("utf-8", "ignore")
        fmts = re.findall(r'<w:numFmt\s+w:val="([^"]+)"', xml)
        texts = re.findall(r'<w:lvlText\s+w:val="([^"]*)"', xml)
        return list(zip(fmts[:9], texts[:9]))
    except Exception:
        return []


def docx_revisions(path):
    """מנתח מסמך עם שינויים במעקב ומחזיר את מחברי השינויים ואת טקסט הבסיס.

    למה זה חשוב: תיקייה של הסכמים שחזרו ממשא ומתן מכילה רק מסמכי redline,
    ואין בה תבנית נקייה. אבל הנייר של הלקוח נמצא שם, בטקסט הבסיס: אם הצד
    שכנגד סימן שינויים על הטופס שלנו, דחיית כל השינויים מחזירה את הטופס שלנו.
    ואם אנחנו סימנו על הטופס שלהם, הבסיס הוא דווקא הנייר שלהם. לכן חייבים
    לדעת מי המחבר, ולא לנחש.
    """
    out = {"authors_ins": {}, "authors_del": {}, "n_ins": 0, "n_del": 0,
           "base_text": "", "final_text": ""}
    try:
        with zipfile.ZipFile(path) as z:
            if "word/document.xml" not in z.namelist():
                return out
            xml = z.read("word/document.xml").decode("utf-8", "ignore")
    except Exception:
        return out
    for tag, key in (("ins", "authors_ins"), ("del", "authors_del")):
        for a in re.findall(r'<w:%s [^>]*w:author="([^"]+)"' % tag, xml):
            out[key][a] = out[key].get(a, 0) + 1
    out["n_ins"] = sum(out["authors_ins"].values())
    out["n_del"] = sum(out["authors_del"].values())

    def strip(blob, drop_tag, keep_tag):
        # מסירים את הבלוקים של drop_tag על תוכנם, ומשאירים את keep_tag
        blob = re.sub(r"<w:%s\b[^>]*>.*?</w:%s>" % (drop_tag, drop_tag), "", blob, flags=re.S)
        txt = " ".join(re.findall(r"<w:t[^>]*>(.*?)</w:t>", blob, re.S))
        txt = re.sub(r"<[^>]+>", "", txt)
        return re.sub(r"\s+", " ", txt).strip()

    # טקסט הבסיס: דוחים את ההוספות ומשאירים את המחוק (delText)
    base = re.sub(r"<w:delText([^>]*)>", r"<w:t\1>", xml)
    base = re.sub(r"</w:delText>", "</w:t>", base)
    out["base_text"] = strip(base, "ins", "del")[:200000]
    # הטקסט הסופי: מקבלים את ההוספות ומסירים את המחיקות
    out["final_text"] = strip(xml, "del", "ins")[:200000]
    return out


def pdf_text(path):
    """(טקסט, סיבה). pymupdf קודם: pypdf מחזיר עברית בסדר חזותי, הפוך, ואז סימני הנייר החוזי אינם
    נמצאים. PDF בעברית בלי pymupdf, או PDF סרוק, מחזיר טקסט ריק, והסיבה נרשמת בתור הבדיקה."""
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        with fitz.open(path) as d:
            return "\n".join(pg.get_text() for pg in d)[:200000], ""
    except ImportError:
        pass
    except Exception:
        return "", "לא ניתן היה לפתוח את ה-PDF"
    try:
        from pypdf import PdfReader
        txt = "\n".join((pg.extract_text() or "") for pg in PdfReader(path).pages)[:200000]
    except Exception:
        return "", "אין בסביבה ספרייה לקריאת PDF (pymupdf)"
    if HE.search(txt):
        return "", "PDF בעברית, ואין pymupdf: הטקסט יוצא בסדר הפוך"
    return txt, ""


READ_EXT = (".docx", ".txt", ".md", ".pdf")
# תיקיות ותוצרים של Areo אינם מקור: תיקיית הנתונים, ותוצרים שהסוכנים כותבים (דף ליווי, גיליון העמדות לאישור,
# מרכז ההיערכות, דוחות). בלי זה גיליון העמדות נרשם כנייר החברה, ומשפחה שאין בה נייר של החברה נראית כאילו יש
AREO_DIRS = ("Areo-נתונים",)
AREO_OUTPUT = re.compile(r"דף ליווי|cover note|עמדות[\s_-]*לאישור|positions[\s_-]*for[\s_-]*approval|areo workspace|"
                         r"מרכז היערכות|prep cent(?:er|re)|דוח שלמות|completeness report|translation-integrity|"
                         r"integrity-|risk-register|תזכיר פנימי|internal memo|\.report\.json$", re.I)
# תיקייה שבשמה מסומן שהמסמכים בה של הצד השני: הנייר שלהם, לעולם לא נייר החברה
COUNTERPARTY_DIR = re.compile(r"מהצד[\s_-]*שכנגד|הצד[\s_-]*השני|מהצד[\s_-]*השני|counterparty|from[\s_-]*them|their[\s_-]*paper",
                              re.I)


def eml_parts(path):
    """(גוף המייל כטקסט, [(שם צרופה, בייטים)]). מייל עם הסכם מצורף נקרא דרך הצרופה; הגוף נשמר לסיווג."""
    import email
    from email import policy
    with open(path, "rb") as fh:
        msg = email.message_from_binary_file(fh, policy=policy.default)
    body = ""
    try:
        part = msg.get_body(preferencelist=("plain", "html"))
        if part is not None:
            body = part.get_content()
            if part.get_content_type() == "text/html":
                body = re.sub(r"<[^>]+>", " ", body)
    except Exception:  # noqa: BLE001  גוף שאינו נקרא: נשארות הצרופות
        body = ""
    atts = []
    for part in msg.iter_attachments():
        name = part.get_filename() or ""
        try:
            data = part.get_payload(decode=True) or b""
        except Exception:  # noqa: BLE001
            data = b""
        if name:
            atts.append((os.path.basename(name), data))
    return re.sub(r"\s+", " ", body or "").strip(), atts


def eml_attachment_dir(path):
    """תיקייה זמנית לצרופות של מייל: בתיקייה הזמנית של המחשב, לעולם לא בתיקיית הלקוח."""
    import tempfile
    h = hashlib.sha256(os.path.abspath(path).encode("utf-8", "ignore")).hexdigest()[:12]
    d = os.path.join(tempfile.gettempdir(), "areo-eml", h)
    os.makedirs(d, exist_ok=True)
    return d


def scan_items(folder, queue):
    """(שם קובץ, תיקייה, נתיב, תוספות) לכל קובץ שאפשר לקרוא. מייל (.eml) נפתח לצרופות שלו. כל מה שאינו נקרא נרשם
    בתור הבדיקה עם הסיבה, ולעולם אינו נעלם בשקט."""
    for root, dirs, files in os.walk(folder):
        for x in [x for x in dirs if x in AREO_DIRS]:
            queue.append({"file": x + "/", "folder": root, "why": "תיקיית הנתונים של Areo אינה מקור", "excluded": True})
        dirs[:] = sorted(x for x in dirs if x not in AREO_DIRS and not x.startswith("."))
        cp = bool(COUNTERPARTY_DIR.search(os.path.relpath(root, folder))) if root != folder else False
        for f in sorted(files):
            if f.startswith("~$") or f.startswith("."):
                continue          # קובץ נעילה או קובץ מערכת, לא מסמך
            path = os.path.join(root, f)
            ext = os.path.splitext(f)[1].lower()
            if AREO_OUTPUT.search(f):
                queue.append({"file": f, "folder": root, "why": "תוצר של Areo, אינו מקור", "excluded": True})
                continue
            extra = {"paper": "counterparty", "paper_basis": "folder"} if cp else {}
            if ext == ".eml":
                try:
                    body, atts = eml_parts(path)
                except Exception as e:  # noqa: BLE001
                    queue.append({"file": f, "folder": root, "why": "לא ניתן היה לקרוא את המייל (%s)" % type(e).__name__})
                    continue
                readable = [(n, b) for n, b in atts if os.path.splitext(n)[1].lower() in READ_EXT]
                for n, b in atts:
                    if (n, b) not in readable:
                        queue.append({"file": "%s / %s" % (f, n), "folder": root,
                                      "why": "צרופה מסוג שאינו נקרא (%s)" % (os.path.splitext(n)[1] or "בלי סיומת")})
                if not readable:
                    queue.append({"file": f, "folder": root, "why": "מייל בלי צרופה שאפשר לקרוא; הגוף אינו הסכם"
                                  if body else "מייל בלי גוף ובלי צרופה שאפשר לקרוא"})
                d = eml_attachment_dir(path) if readable else None
                for n, b in readable:
                    ap = os.path.join(d, n)
                    with open(ap, "wb") as fh:
                        fh.write(b)
                    yield n, d, ap, dict(extra, source_email=path)
                continue
            if ext not in READ_EXT:
                queue.append({"file": f, "folder": root, "why": "סוג קובץ שאינו נקרא (%s)" % (ext or "בלי סיומת")})
                continue
            yield f, root, path, extra


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return docx_text(path)
    if ext == ".pdf":
        return pdf_text(path)[0], False, False
    if ext in (".txt", ".md"):
        try:
            return io.open(path, encoding="utf-8", errors="ignore").read()[:200000], False, False
        except Exception:
            return "", False, False
    return "", False, False

AGR_WORD = re.compile(r"(?:הסכם|חוזה|agreement|contract)\s*", re.I)
NOISE = re.compile(r"redline|final|draft|signed|v\d|\d{1,2}[-.]\d{1,2}[-.]\d{2,4}|"
                   r"טיוטה|חתום|סופי|מעודכן|עותק|\(\d+\)", re.I)
# שם עצם שה-ה' שבראשו היא אות שורש ולא ה' הידיעה: בניין התפעל ("התקשרות", "התחייבות") ושם פעולה של
# הפעיל. ה' הידיעה לפניו כתובה כפולה ("ההתקשרות")
HE_INITIAL_NOUN = re.compile(r"^(?:הת[א-ת]{2,}|ה[א-ת]{2,4}ה|ה[א-ת]{2,3}ת)$")


def strip_article(word):
    """מסיר את ה' הידיעה מהמילה שאחרי "הסכם" ("הסכם השירותים" -> "שירותים"), אבל לא אות שורש
    (מילה שאחרי "הסכם" שאות שורש ראשונה בה היא ה'). בספק, ה' נשארת: מילה שלמה עם ה'
    עדיפה על מילה שאיבדה אות."""
    if word.startswith("הה"):
        return word[1:]
    if word.startswith("ה") and len(word) > 3 and not HE_INITIAL_NOUN.match(word):
        return word[1:]
    return word


def derive_family_name(fname):
    """גוזר שם משפחה מוצע משם הקובץ, כשאין התאמה לרשימת הזרע.

    המערכת מותקנת אצל כל חברה ובכל תחום משפטי. רשימה סגורה של משפחות תשאיר
    שליש מהתיקייה בלי סיווג אצל לקוח שעוסק בקבלנות, בניסויים קליניים או
    במיזוגים. במקום זה, השם נגזר מהמילים שאחרי "הסכם" בשם הקובץ, ומוצג
    למשתמש כהצעה. הוא לעולם אינו נקבע בלי אישור.
    """
    base = os.path.splitext(fname)[0]
    base = NOISE.sub(" ", base)
    base = re.sub(r"[_\-]+", " ", base)
    m = AGR_WORD.search(base)
    if m:
        base = base[m.end():]
    STOP = {"for", "of", "the", "and", "with", "between", "to", "by", "on",
            "בין", "עם", "של", "על", "לבין", "מול"}
    words = [w for w in re.split(r"\s+", base.strip())
             if len(w) > 1 and w.lower() not in STOP]
    if m and words:
        words[0] = strip_article(words[0])
    # שמות פרטיים של צדדים הם בדרך כלל המילים האחרונות; שומרים את השתיים הראשונות
    cand = " ".join(words[:2]).strip(" ,.-")
    return cand if 2 <= len(cand) <= 40 else None


def pick_family(name, head, body):
    """המשפחה נגזרת בזמן ריצה מהמסמך של הלקוח עצמו: שם הקובץ קודם, ואז שורות הכותרת. אין רשימת סוגים בקוד.
    ללא שם מתאים: "לא זוהתה משפחה", והמשתמש נשאל. הצעה אינה נקבעת בלי אישור."""
    for src, why in ((name, "נגזר משם הקובץ, טעון אישור המשתמש"),
                     ((head or "").strip().splitlines()[0] if (head or "").strip() else "",
                      "נגזר מכותרת המסמך, טעון אישור המשתמש")):
        cand = derive_family_name(src) if src else None
        if cand:
            return cand, [cand], why
    return None, [], "לא זוהתה משפחה"


def pick_role(text):
    """אין זיהוי תפקיד לפי ספירת מילים: תפקיד החברה בא מהמשתמש או מהפלייבוק, ואחרת נשאל."""
    return []


def normalize_role(value):
    """--role או company_role_code: טקסט חופשי בלשון הלקוח, בלי מילון. other או ריק: אין תפקיד."""
    v = (value or "").strip()
    if not v or v.lower() == "other":
        return None
    return v


def playbook_roles(path):
    """[(שמות המשפחה, תפקיד)] מ-contract_families[] של הפלייבוק, בכל עומק של הקובץ."""
    out = []
    try:
        data = json.load(io.open(path, encoding="utf-8"))
    except Exception:
        return out
    stack = [data]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            for f in x.get("contract_families") or []:
                if isinstance(f, dict) and normalize_role(f.get("company_role_code")):
                    names = [f.get("contract_family_name"), f.get("contract_family_id")] + list(f.get("family_aliases") or [])
                    out.append(([n for n in names if n], normalize_role(f.get("company_role_code"))))
            stack.extend(v for v in x.values() if isinstance(v, (dict, list)))
        elif isinstance(x, list):
            stack.extend(x)
    return out


def family_matches(family, names):
    """האם משפחת המרשם היא המשפחה של הפלייבוק: שם זהה, או אחד מכיל את השני כמילה שלמה."""
    if not family:
        return False
    strip = lambda s: re.sub(r"^(?:הסכמי|הסכם)\s+|\s+agreements?$|_", " ", s.lower()).strip()
    f = strip(family)
    for n in names:
        n = strip(str(n))
        if f and n and (f == n or word_count(f, n) or word_count(n, f)):
            return True
    return False


def parse_roles(values):
    """--role: "receiving" לכל המסמכים, או "סודיות=receiving" למשפחה אחת. [(שמות או None, תפקיד)],
    המשפחתיים קודם."""
    out = []
    for v in values or []:
        fam, _, role = v.rpartition("=")
        role = normalize_role(role)
        if role:
            out.append(([fam.strip()] if fam.strip() else None, role))
    return sorted(out, key=lambda x: x[0] is None)


def resolve_role(family, body, role_arg, pb_roles):
    """(תפקיד החברה, בסיס, מועמדים). קודם מה שהמשתמש מסר (--role), אחר כך company_role_code של
    פלייבוק לאותה משפחה, ורק בלעדיהם ספירת מילים, שמסומנת כטעונה אישור."""
    counted = pick_role(body)
    for names, role in role_arg:
        if names is None or family_matches(family, names):
            return role, "המשתמש (--role)", [role] + [r for r in counted if r != role]
    for names, role in pb_roles:
        if family_matches(family, names):
            return role, "company_role_code בפלייבוק", [role] + [r for r in counted if r != role]
    return None, "תפקיד לא ידוע, שאלה למשתמש", []


def _alias_key(g):
    g = re.sub(r"\s+", " ", re.sub(r"_{2,}|\.{3,}", " ", g or "")).strip(" .,:;").lower()
    return re.sub(r"^the\s+", "", g)


def blank_parties(text):
    """כינויי הצדדים שפרטיהם ריקים בפתיח (עד 2500 תווים): "________ (להלן: "<תפקיד>")"."""
    out = []
    for m in BLANK_PARTY.finditer((text or "")[:2500]):
        g = re.sub(r"\s+", " ", m.group(1)).strip()
        if g and g not in out:
            out.append(g)
    return out


DEFINED_ALIAS = re.compile(r'(?:להלן\s*[:\-]?\s*|hereinafter(?:\s+(?:referred\s+to\s+as|called))?\s*[:,]?\s*(?:the\s+)?'
                           r'|the\s+)?["״“]([^"״”()]{2,40})["״”]', re.I)


def whose_template(blanks, role, body=""):
    """counterparty, company או None: הצד הריק בפתיח הוא הצד של החברה (טופס של הצד שכנגד) או הצד שכנגד (תבנית של
    החברה). התפקיד הוא טקסט חופשי (מהמשתמש או מהפלייבוק), והוא נמצא בפתיח כמונח מוגדר, ריק או מלא. None כשהפתיח
    אינו מכריע או כשהתפקיד אינו ידוע."""
    if not role:
        return None
    r = _alias_key(role)
    ours = {r, "ה" + r}
    blank = {_alias_key(g) for g in blanks or ()}
    defined = {_alias_key(m.group(1)) for m in DEFINED_ALIAS.finditer((body or "")[:2500])}
    if blank & ours:
        return "counterparty"
    if blank and (defined & ours):
        return "company"
    return None


def paper_owner(name, body, blanks, role, role_basis):
    """(counterparty או company או None, הסיבה) לטופס עם שדות למילוי. הצד הריק בפתיח קודם, כשהתפקיד ידוע (מהמשתמש
    או מהפלייבוק, לא מספירת מילים); אחריו נוסח של הליך תחרותי, כשהחברה אינה הגוף המזמין."""
    known = role and not str(role_basis or "").startswith("תפקיד לא ידוע")
    owner = whose_template(blanks, role, body) if known else None
    if owner == "counterparty":
        return owner, "הצד שפרטיו ריקים בפתיח הוא הצד של החברה"
    if owner == "company":
        return owner, "הצד שפרטיו ריקים בפתיח הוא הצד שכנגד"
    m = PROCEDURE_SIGN.search(os.path.splitext(name)[0]) or PROCEDURE_SIGN.search(body or "")
    if m and (role or "").strip().lower() not in ISSUER_WORDS:
        return "counterparty", "נוסח של הליך תחרותי (%s), והחברה אינה הגוף המזמין" % m.group(0)
    return None, None


def mutuality(name, head):
    """mutual, one_way או None, לפי שם הקובץ ושורות הכותרת בלבד."""
    area = name + "\n" + head
    if ONE_WAY.search(area):
        return "one_way"
    if MUTUAL.search(area):
        return "mutual"
    return None


def language(text):
    he = len(HE.findall(text)); lat = len(LAT.findall(text))
    if he and lat and min(he, lat) / max(he, lat) > 0.25:
        return "bilingual"
    return "he" if he >= lat else "en"

# שם חברה בלי סיומת התאגדות: "אורבן תשתיות בע"מ", "אורבן תשתיות בעמ" ו"אורבן תשתיות" הם אותה חברה. גם עמותה
# (ע"ר), חל"צ ו-charity באנגליה (CIO, CIC), עם סוגריים או בלעדיהם: הצד אינו תמיד חברה בע"מ
CORP_SUFFIX = re.compile(r"\s*\(?(?:בע[\"'״׳]?מ|ע[\"'״׳]ר|חל[\"'״׳]?צ|ltd\.?|limited|inc\.?|llc|plc|gmbh|"
                         r"cio|cic|corp(?:oration)?\.?|co\.)\)?\s*$", re.I)
RECITALS = re.compile(r"הואיל|whereas|recitals|מבוא", re.I)


def _norm_name(v):
    v = re.sub(r"[\"'״׳`]", "", str(v or "").lower())
    return re.sub(r"\s+", " ", v).strip()


def company_markers(profile_path, extra):
    """(שמות, מספרי רישום) של החברה: organization_name, organization_name_en ו-registration_number מהפרופיל,
    ו---company."""
    prof = {}
    if profile_path and os.path.exists(profile_path):
        try:
            prof = json.load(io.open(profile_path, encoding="utf-8"))
        except Exception:
            prof = {}
    names, regs = [], []
    for n in [prof.get("organization_name"), prof.get("organization_name_en")] + list(extra or []):
        core = _norm_name(CORP_SUFFIX.sub("", str(n or "").strip()))
        if len(core) >= 3 and core not in names:
            names.append(core)
    for r in (prof.get("registration_number"), prof.get("organization_id")):
        digits = re.sub(r"\D", "", str(r or ""))
        if len(digits) >= 6 and digits not in regs:
            regs.append(digits)
    return names, regs


def on_company_paper(body, names, regs):
    """האם החברה היא צד בבלוק הצדדים: מתחילת המסמך ועד המבוא, ולכל היותר 3,000 תווים.
    None כשלא נמסר שם חברה, ואז אין בדיקה."""
    if not names and not regs:
        return None
    block = body[:3000]
    m = RECITALS.search(block, 100)
    if m:
        block = block[:m.start()]
    low = _norm_name(block)
    if any(n in low for n in names):
        return True
    digits = re.sub(r"\D", "", block)
    return any(r in digits for r in regs)


def classify(text, tracked, comments, name):
    """text הוא גוף המסמך, פסקה בשורה, כדי ששורות הכותרת וסוף המסמך יהיו ידועים."""
    reasons = []
    head = [l.strip()[:200] for l in text.splitlines() if l.strip()][:3]
    if AMEND.search(os.path.splitext(name)[0]) or any(AMEND.search(l) for l in head):
        return "amendment", ["הכותרת או שם הקובץ מזהים תיקון להסכם"]
    if tracked:
        return "internal_draft", ["המסמך מכיל שינויים במעקב"]
    if comments:
        return "internal_draft", ["המסמך מכיל הערות"]
    ph = placeholder_count(text)
    signed = bool(SIGN_DATE.search(text))
    if signed and ph <= 2:
        return "signed", ["אותר תאריך חתימה ואין שדות ריקים מהותיים"]
    if ph >= 3:
        return "template", ["אותרו %d שדות למילוי" % ph]
    if signed:
        return "signed", ["אותר תאריך חתימה"]
    reasons.append("לא אותרו שדות למילוי ולא אותר תאריך חתימה")
    return "unclassified", reasons

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--folders", nargs="+", required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--playbook", help="playbook-model.json: company_role_code של המשפחה שלו קובע את התפקיד")
    p.add_argument("--role", nargs="+", help="הצד שבו עומדת החברה, כפי שמסר המשתמש: קוד (customer, receiving, "
                                             "processor ...) או תווית (לקוח, מקבל, מעבד ...), לכל המסמכים, או "
                                             "משפחה=תפקיד למשפחה אחת. גובר על הפלייבוק ועל ספירת מילים")
    p.add_argument("--profile", help="פרופיל-לקוח.json: שם החברה ומספר הרישום, לבדיקה שהמסמך על נייר החברה")
    p.add_argument("--company", nargs="+", help="שמות נוספים של החברה (שם באנגלית, שם קודם)")
    p.add_argument("--approved", nargs="+", help="שמות קבצים שהמשתמש אישר כתבנית, גם כשאינם על נייר החברה")
    a = p.parse_args()
    guard_out(a.out, [a.playbook, a.profile])
    names, regs = company_markers(a.profile, a.company)
    approved = {os.path.basename(x) for x in (a.approved or [])}
    role_arg = parse_roles(a.role)
    pb_roles = playbook_roles(a.playbook) if a.playbook and os.path.exists(a.playbook) else []

    docs, queue, seen = [], [], {}
    for folder in a.folders:
        for f, root, path, extra in scan_items(folder, queue):
            if True:
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                is_pdf = f.lower().endswith(".pdf")
                if is_pdf:
                    (text, why_pdf), tracked, comments = pdf_text(path), False, False
                else:
                    (text, tracked, comments), why_pdf = read_text(path), ""
                if not text.strip():
                    queue.append({"file": f, "folder": root,
                                  "why": why_pdf or ("PDF סרוק, בלי שכבת טקסט" if is_pdf
                                                     else "לא ניתן היה לקרוא טקסט מהמסמך")})
                    continue
                h = hashlib.sha256(text[:20000].encode("utf-8", "ignore")).hexdigest()[:16]
                if h in seen:
                    docs[seen[h]].setdefault("duplicates", []).append(f)
                    continue
                ok, why_not = is_contract(text, f, os.path.splitext(f)[1].lower())
                if not ok:
                    queue.append({"file": f, "folder": root, "why": why_not,
                                  "excluded": True})
                    continue
                # הגוף פסקה בשורה: docx_text משטח הכול לשורה אחת ומצרף אחריו כותרות עליונות
                # ותחתונות, ואז שורות הכותרת וסוף המסמך (קו החתימה) אינם ידועים
                body = text
                if path.lower().endswith(".docx"):
                    body = "\n".join(docx_paragraphs(path)) or text
                cls, why = classify(body, tracked, comments, f)
                fam, fam_all, fam_conf = pick_family(f, text[:800], text[:20000])
                role, role_basis, roles = resolve_role(fam, text[:20000], role_arg, pb_roles)
                rec = {
                    "file": f, "folder": root, "bytes": size,
                    "doc_class": cls, "class_reason": why,
                    "family": fam, "family_candidates": fam_all, "family_basis": fam_conf,
                    "company_role_candidates": roles,
                    "company_role": role, "company_role_basis": role_basis,
                    "mutuality": mutuality(f, "\n".join(body.splitlines()[:3])),
                    "language": language(text),
                    "doc_date": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d"),
                    "approved_current": False,
                    "format": "pdf" if is_pdf else os.path.splitext(f)[1].lower().lstrip("."),
                    "company_paper": on_company_paper(body, names, regs) and extra.get("paper") != "counterparty",
                    "user_approved": f in approved,
                }
                rec.update(extra)
                if cls == "template":
                    blanks = blank_parties(body)
                    if blanks:
                        rec["blank_parties"] = blanks
                    owner, owner_why = paper_owner(f, body, blanks, role, role_basis)
                    if owner:
                        rec["paper_owner"], rec["paper_owner_basis"] = owner, owner_why
                if is_pdf:
                    rec["selectable_as_template"] = False
                    rec["format_note"] = "PDF: נקרא לסיווג ולמבנה, ואינו נבחר כתבנית. לתבנית יש לשמור אותו כ-docx"
                if tracked:
                    rev = docx_revisions(path)
                    rec["revisions"] = {
                        "authors": sorted(set(list(rev["authors_ins"]) + list(rev["authors_del"]))),
                        "insertions": rev["n_ins"], "deletions": rev["n_del"],
                        "base_text_chars": len(rev["base_text"]),
                        "markup_side": "לא ידוע, טעון שאלה למשתמש",
                        "note": ("מי שסימן את השינויים הוא מי שמנסח את עמדתו. אם המחברים "
                                 "הם אנשי החברה, המרקאפ הוא העמדה שלנו והנוסח שאחרי קבלת "
                                 "השינויים הוא לשון הבית; טקסט הבסיס הוא אז הנייר של הצד "
                                 "שכנגד ואינו התבנית שלנו. אם המחברים הם הצד שכנגד, ההפך. "
                                 "אין להסיק מהשמות: יש לשאול את המשתמש."),
                        "house_text_is": "לא ידוע עד שתיקבע זהות המחברים",
                    }
                if cls == "unclassified" or not fam or fam_conf.endswith("טעון אישור"):
                    queue.append({"file": f, "folder": root,
                                  "why": "; ".join(why + ([] if fam else ["לא זוהתה משפחת הסכם"])
                                                   + ([fam_conf] if fam and fam_conf.endswith("טעון אישור") else []))})
                seen[h] = len(docs)
                docs.append(rec)

    # התבנית המאושרת הנוכחית לכל צירוף. הדדי וחד-צדדי הם צירופים נפרדים
    keyed = {}
    for i, d in enumerate(docs):
        if not d["family"]:
            continue
        role = (d["company_role_candidates"] or ["לא צוין"])[0]
        key = (d["family"], role, d["language"], d.get("mutuality"))
        keyed.setdefault(key, []).append(i)
    def eligible(i):
        # שדות ריקים אינם הופכים מסמך לתבנית של החברה: רק נייר החברה או אישור המשתמש, ולא PDF
        d = docs[i]
        return d["format"] != "pdf" and (d["user_approved"] or (
            d["company_paper"] is True and d.get("paper_owner") != "counterparty"))

    third_party = []
    for key, idxs in keyed.items():
        for i in idxs:
            d = docs[i]
            if d["doc_class"] in ("template", "signed") and not eligible(i):
                d["not_approved_reason"] = (
                    "PDF" if d["format"] == "pdf" else
                    "טופס של הצד שכנגד: " + d["paper_owner_basis"] if d.get("paper_owner") == "counterparty" else
                    "לא נמסר שם החברה (--profile), ולכן לא נבדק שהמסמך על נייר החברה" if d["company_paper"] is None
                    else "שם החברה אינו בבלוק הצדדים: נייר של צד שלישי")
                if d.get("paper_owner") == "company":
                    d["not_approved_reason"] += ("; הצד שפרטיו ריקים בפתיח הוא הצד שכנגד, ולכן ייתכן שזו תבנית של "
                                                 "החברה")
                if d["doc_class"] == "template" and d["format"] != "pdf":
                    queue.append({"file": d["file"], "folder": d["folder"],
                                  "why": "טופס עם שדות למילוי שלא נבחר כתבנית מאושרת: " + d["not_approved_reason"]
                                         + ". אם המשתמש מאשר אותו כתבנית, הרץ שוב עם --approved"})
        if not any(eligible(i) for i in idxs):
            third_party.append({"family": key[0], "role": key[1], "language": key[2], "mutuality": key[3],
                                "documents": [docs[i]["file"] for i in idxs]})
        idxs = [i for i in idxs if eligible(i)]
        templates = [i for i in idxs if docs[i]["doc_class"] == "template"]
        pool = templates or [i for i in idxs if docs[i]["doc_class"] == "signed"]
        basis = "template" if templates else ("signed" if pool else None)
        if not pool:
            # תיקייה של הסכמים שחזרו ממשא ומתן מכילה רק redline, ואין בה תבנית
            # נקייה. במקרה כזה טקסט הבסיס של ה-redline העדכני ביותר הוא הבסיס
            # הטוב ביותר שיש, ובלבד שהוא מסומן ככזה וטעון אישור המשתמש.
            pool = [i for i in idxs if docs[i].get("revisions")]
            basis = "redline_base" if pool else None
        if not pool:
            continue
        best = max(pool, key=lambda i: docs[i]["doc_date"])
        docs[best]["approved_current_basis"] = basis
        docs[best]["approved_by"] = "company_paper" if docs[best]["company_paper"] else "user"
        if basis == "redline_base":
            docs[best]["approved_current_note"] = (
                "אין בתיקייה תבנית נקייה ואין הסכם חתום, והבסיס נגזר ממסמך redline. "
                "**אין להשתמש בו כלשון בית לפני שנקבע מי סימן את השינויים.** "
                "אם אנשי החברה סימנו, לשון הבית היא הנוסח שאחרי קבלת השינויים, וטקסט "
                "הבסיס הוא נייר הצד שכנגד. אם הצד שכנגד סימן, ההפך. שאל את המשתמש "
                "שאלה אחת: מי הם מחברי השינויים שבמסמך, אנשי החברה או הצד שכנגד.")
            docs[best]["requires_user_answer"] = "מי סימן את השינויים במסמך"
        docs[best]["approved_current"] = True
        if not templates:
            docs[best]["derived_from_signed"] = True

    out = {
        "meta": {
            "generated_at": datetime.now().strftime("%Y-%m-%d"),
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "folders": list(a.folders),
            "playbook_used": bool(a.playbook and os.path.exists(a.playbook)),
            "company_paper_checked": bool(names or regs),
            # צירופים שיש בהם מסמכים ואף אחד מהם אינו על נייר החברה או מאושר: המנסח עובד בהם במצב 2ב
            "third_party_paper_only": third_party,
            "note": "מרשם נגזר. הרכיב מציג אותו למשתמש ומבקש אישור לפני הסתמכות.",
        },
        "documents": docs,
        "review_queue": queue,
    }
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    io.open(a.out, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    by_class = {}
    for d in docs:
        by_class[d["doc_class"]] = by_class.get(d["doc_class"], 0) + 1
    print("נסרקו %d מסמכים ייחודיים" % len(docs))
    for k, v in sorted(by_class.items(), key=lambda x: -x[1]):
        print("  %-20s %d" % (k, v))
    print("תבניות מאושרות שנקבעו: %d" % sum(1 for d in docs if d["approved_current"]))
    pdfs = sum(1 for d in docs if d["format"] == "pdf")
    if pdfs:
        print("PDF שנקראו ונרשמו: %d (אינם נבחרים כתבנית)" % pdfs)
    if not (names or regs):
        print("שים לב: לא נמסר שם החברה (--profile), ולכן אף מסמך לא נבחר כתבנית מאושרת")
    elif third_party:
        print("צירופים בלי אף מסמך על נייר החברה: %d" % len(third_party))
    excluded = sum(1 for q in queue if q.get("excluded"))
    print("בתור בדיקה: %d, מתוכם %d הוצאו (לא חוזי, תוצר של Areo או תיקיית הנתונים)" % (len(queue), excluded))
    not_read = [q for q in queue if not q.get("excluded")]
    for q in not_read[:20]:
        print("  לא נקרא: %s (%s)" % (q["file"], q["why"]))

if __name__ == "__main__":
    main()
