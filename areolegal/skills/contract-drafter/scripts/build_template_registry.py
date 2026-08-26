# -*- coding: utf-8 -*-
"""סורק את תיקיות ההסכמים המחוברות ובונה את מרשם התבניות של הלקוח.

שימוש:
  python3 build_template_registry.py --folders "<תיקייה>" ["<תיקייה נוספת>" ...] \
      --out "Areo-נתונים/template-registry.json" [--playbook "Areo-נתונים/playbook-model.json"]

הסקריפט מסווג כל מסמך ומחשב, לכל צירוף של משפחה, תפקיד ושפה, מי התבנית המאושרת הנוכחית.
הוא אינו ממציא סיווג: מסמך שאינו ניתן לסיווג חד-משמעי נכנס לתור בדיקה עם ציון הסיבה.

זיהוי הסיווג נשען על סימנים בטקסט ובמבנה הקובץ בלבד. הוא כלי עזר לרכיב, לא תחליף לשיקול דעת:
הרכיב מציג את המרשם למשתמש ומבקש אישור לפני שהוא מסתמך עליו.
"""
import argparse, hashlib, io, json, os, re, sys, zipfile
from datetime import datetime

PLACEHOLDER = re.compile(r"\[להשלים\]|\[TO COMPLETE\]|_{4,}|\bXXX+\b|\[\s{2,}\]|\[●\]|\[\*+\]")
SIGN_DATE = re.compile(
    r"(?:נחתם|תאריך החתימה|Signed on|Date of signature)\s*[:\-]?\s*\d"
    r"|ולראיה\s+באו\s+הצדדים\s+על\s+החתום"
    r"|IN\s+WITNESS\s+WHEREOF"
    r"|ובאו\s+הצדדים\s+על\s+החתום", re.I)

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
# "MSA Final" הם שמות אמיתיים של הסכמים, והדרישה שהשם ייפתח במילה חסמה אותם.
CONTRACT_TITLE = re.compile(
    r"הסכם|חוזה|תוספת|נספח|agreement|contract|addendum|amendment|"
    r"\bagr\b|\bnda\b|\bmou\b|\bloi\b|\bmsa\b|\bsow\b|reseller|distribution|license", re.I)

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
AMEND = re.compile(r"תיקון\s+(?:מס['׳]?\s*\d+\s+)?להסכם|נספח\s+תיקון|amendment|addendum", re.I)
HE = re.compile(r"[֐-׿]")
LAT = re.compile(r"[A-Za-z]")

ROLES = {
    "לקוח": ["הלקוח", "המזמין", "customer", "client"],
    "ספק": ["הספק", "נותן השירותים", "supplier", "vendor", "service provider"],
    "מרשה": ["המרשה", "נותן הרישיון", "licensor"],
    "מורשה": ["המורשה", "מקבל הרישיון", "licensee"],
    "משכיר": ["המשכיר", "lessor", "landlord"],
    "שוכר": ["השוכר", "lessee", "tenant"],
    "מזכה": ["המזכה", "franchisor"],
    "זכיין": ["הזכיין", "franchisee"],
    "מבוטח": ["המבוטח", "insured"],
    "מבטח": ["המבטח", "insurer"],
}

# מילות המפתח ממוינות לפי סגוליות: מונח ארוך וסגולי גובר על מונח כללי.
# "זכיינות" חייב לגבור על "רישוי", ו"ליסינג" חייב להיות משפחה בפני עצמה.
FAMILIES = [
    ("סודיות", ["הסכם סודיות", "אי גילוי", "שמירת סודיות", "non-disclosure", "confidentiality agreement", "nda"]),
    ("שירותים", ["הסכם מסגרת שירותים", "הסכם שירותים", "מתן שירותים", "מיקור חוץ", "outsourcing", "services agreement", "master services", "msa"]),
    ("רישוי תוכנה", ["רישוי תוכנה", "רישיון שימוש בתוכנה", "saas", "software license", "subscription agreement"]),
    ("הפצה וזכיינות", ["זכיינות", "הסכם הפצה", "זיכיון", "reseller", "distribution agreement", "franchise"]),
    ("ליסינג וחכירה", ["ליסינג", "חכירת", "חכירה", "leasing", "equipment lease"]),
    ("שכירות", ["הסכם שכירות", "שכירות מסחרית", "דמי שכירות", "lease agreement", "tenancy"]),
    ("העסקה", ["הסכם העסקה", "חוזה עבודה אישי", "employment agreement"]),
    ("ביטוח", ["הסכם ביטוח", "פוליסת ביטוח", "אחריות מקצועית", "insurance policy"]),
    ("רכש", ["הזמנת רכש", "הסכם רכש", "purchase order", "procurement agreement"]),
    ("פיתוח ומחקר", ["הסכם פיתוח", "פיתוח תוכנה", "מחקר ופיתוח", "ניסוי קליני",
                     "development agreement", "research agreement", "clinical trial",
                     "statement of work", "sow"]),
    ("קבלנות ובנייה", ["הסכם קבלנות", "עבודות בנייה", "ביצוע עבודות", "קבלן ראשי",
                       "construction agreement", "works contract", "epc"]),
    ("מיזוג ורכישה", ["מיזוג", "רכישת מניות", "רכישת פעילות", "הסכם מייסדים",
                      "share purchase", "asset purchase", "merger", "spa", "founders"]),
    ("מימון ואשראי", ["הסכם הלוואה", "מסגרת אשראי", "שטר הון", "ערבות בנקאית להלוואה",
                      "loan agreement", "credit facility", "convertible"]),
    ("שיתוף פעולה ומיזם משותף", ["שיתוף פעולה", "מיזם משותף", "הסכם שותפות",
                                 "joint venture", "collaboration agreement", "teaming"]),
    ("סוכנות ותיווך", ["הסכם סוכנות", "עמלת תיווך", "מתווך", "agency agreement", "broker"]),
]

# הרשימה שלמעלה היא **זרע ולא גבול.** אצל לקוח אחד יש הסכמי קבלנות, אצל אחר
# הסכמי ניסוי קליני, ואצל שלישי הסכמים שאין להם שם מקובל בכלל. משפחה שאינה
# ברשימה נלמדת משם הקובץ של הלקוח עצמו, ומאושרת מולו. ראה derive_family_name.
FAMILY_EXT_FILE = "family-extensions.json"

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


def read_text(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".docx":
        return docx_text(path)
    if ext in (".txt", ".md"):
        try:
            return io.open(path, encoding="utf-8", errors="ignore").read()[:200000], False, False
        except Exception:
            return "", False, False
    return "", False, False

AGR_WORD = re.compile(r"(?:הסכם|חוזה|agreement|contract)\s*(?:ה)?", re.I)
NOISE = re.compile(r"redline|final|draft|signed|v\d|\d{1,2}[-.]\d{1,2}[-.]\d{2,4}|"
                   r"טיוטה|חתום|סופי|מעודכן|עותק|\(\d+\)", re.I)


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
    # שמות פרטיים של צדדים הם בדרך כלל המילים האחרונות; שומרים את השתיים הראשונות
    cand = " ".join(words[:2]).strip(" ,.-")
    return cand if 2 <= len(cand) <= 40 else None


def pick_family(name, head, body):
    """שם הקובץ והכותרת גוברים על הגוף. בגוף כל הסכם מוזכרים ביטוח, סודיות ורכש,
       ולכן ספירה בגוף לבדה מסווגת שגוי כמעט תמיד."""
    nm, hd, bd = name.lower(), head.lower(), body.lower()
    scored = []
    for label, words in FAMILIES:
        # מונח ארוך יותר הוא סגולי יותר, ולכן משקלו גבוה יותר
        w_name = sum(4 + len(w) for w in words if w.lower() in nm)
        w_head = sum(2 + len(w) // 2 for w in words if w.lower() in hd)
        w_body = sum(min(bd.count(w.lower()), 4) for w in words)
        total = w_name + w_head + w_body
        if total:
            scored.append((w_name + w_head, total, label))
    if not scored:
        cand = derive_family_name(name)
        if cand:
            return cand, [cand], "נגזר משם הקובץ, טעון אישור המשתמש"
        return None, [], "לא זוהתה משפחה"
    # קודם מי שזוהה בשם או בכותרת, ורק אז לפי הגוף
    scored.sort(reverse=True)
    top = scored[0]
    conf = "שם הקובץ או הכותרת" if top[0] > 0 else "גוף המסמך בלבד, טעון אישור"
    return top[2], [x[2] for x in scored[:3]], conf

def pick_role(text):
    low = text.lower()
    scored = []
    for label, words in ROLES.items():
        n = sum(low.count(w.lower()) for w in words)
        if n:
            scored.append((n, label))
    scored.sort(reverse=True)
    return [l for _, l in scored[:2]]

def language(text):
    he = len(HE.findall(text)); lat = len(LAT.findall(text))
    if he and lat and min(he, lat) / max(he, lat) > 0.25:
        return "bilingual"
    return "he" if he >= lat else "en"

def classify(text, tracked, comments, name):
    reasons = []
    if AMEND.search(name) or AMEND.search(text[:4000]):
        return "amendment", ["הכותרת או הפתיח מזהים תיקון להסכם"]
    if tracked:
        return "internal_draft", ["המסמך מכיל שינויים במעקב"]
    if comments:
        return "internal_draft", ["המסמך מכיל הערות"]
    ph = len(PLACEHOLDER.findall(text))
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
    p.add_argument("--playbook")
    a = p.parse_args()

    docs, queue, seen = [], [], {}
    for folder in a.folders:
        for root, _dirs, files in os.walk(folder):
            for f in sorted(files):
                if f.startswith("~$") or os.path.splitext(f)[1].lower() not in (".docx", ".txt", ".md"):
                    continue
                path = os.path.join(root, f)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                text, tracked, comments = read_text(path)
                if not text.strip():
                    queue.append({"file": f, "folder": root, "why": "לא ניתן היה לקרוא טקסט מהמסמך"})
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
                cls, why = classify(text, tracked, comments, f)
                fam, fam_all, fam_conf = pick_family(f, text[:800], text[:20000])
                roles = pick_role(text[:20000])
                rec = {
                    "file": f, "folder": root, "bytes": size,
                    "doc_class": cls, "class_reason": why,
                    "family": fam, "family_candidates": fam_all, "family_basis": fam_conf,
                    "company_role_candidates": roles,
                    "language": language(text),
                    "doc_date": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d"),
                    "approved_current": False,
                }
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

    # התבנית המאושרת הנוכחית לכל צירוף
    keyed = {}
    for i, d in enumerate(docs):
        if not d["family"]:
            continue
        role = (d["company_role_candidates"] or ["לא צוין"])[0]
        key = (d["family"], role, d["language"])
        keyed.setdefault(key, []).append(i)
    for key, idxs in keyed.items():
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
    excluded = sum(1 for q in queue if q.get("excluded"))
    print("בתור בדיקה: %d, מתוכם %d הוצאו כמסמכים שאינם חוזיים" % (len(queue), excluded))

if __name__ == "__main__":
    main()
