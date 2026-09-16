# -*- coding: utf-8 -*-
"""כללי המקורות של מצב 4 (אין בתיקייה דבר מסוג ההסכם), כקוד ולא כהמלצה.

שני סוגי מקורות, ולכל אחד תפקיד אחר:
  law         הדין שחל על ההסכם. **רק אתר הכנסת ואתרי gov.il**, כולל תת-דומיינים
              כמו mr.gov.il. מקור אחר אינו בסיס לקביעת דין, גם אם הוא נכון.
  structures  הסכמים דומים שמהם נלקח **המבנה**: אילו נושאים יש, ובאיזה סדר. לא נוסח.
              3 לפחות, 7 לכל היותר, ועוצרים כשהסכם נוסף אינו מוסיף נושא חדש.

הבדיקות כאן חוסמות רק את מה שאסור באמת: מקור דין מאתר שאינו רשמי, ויותר משבעה
מקורות מבנה. כל השאר (מקור שלא נפתח, תבנית ממשלתית כשהלקוח ספק, מקור פרטי) הוא
סימון שעובר למסמך האישור ולנספח המקורות, כדי שעורך הדין יראה אותו.
"""
import re

try:                                   # Python 3
    from urllib.parse import urlparse
except ImportError:                    # pragma: no cover
    from urlparse import urlparse

LAW_EFFECTS = ("סעיף חובה", "איסור", "חובת גילוי", "דרישת רישום", "הגבלה", "אחר")
STRUCTURE_TYPES = ("רגולטור", "גוף ציבורי", "ממשלתי-מכרז", "משרד עורכי דין", "אתר משפטי", "אחר")
# a standard form a regulator or public body publishes may be used as worded, with the
# source named. Everything else lends its structure only.
VERBATIM_OK = ("רגולטור", "גוף ציבורי")
MIN_STRUCTURES, TARGET_STRUCTURES, MAX_STRUCTURES = 3, 5, 7


def host(url):
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def is_official_law_source(url):
    h = host(url)
    return h == "gov.il" or h.endswith(".gov.il")


def is_government(url):
    return is_official_law_source(url) and "knesset" not in host(url)


def check(research):
    """מחזיר (blocking, flags, notes). blocking: רשימת מחרוזות שעוצרות את המחקר.
    flags: לכל מקור, סימונים שמוצגים לידו. notes: הערות כלליות למסמך האישור."""
    blocking, notes = [], []
    flags = {"law": [], "structures": []}
    role = (research.get("company_role") or "").strip()

    law = research.get("law") or []
    if not law:
        blocking.append("אין אף מקור דין. מיפוי הדין הוא החלק הראשון של המחקר, ובלעדיו אין טיוטה.")
    for i, src in enumerate(law):
        f = []
        if not is_official_law_source(src.get("url", "")):
            blocking.append("מקור דין %d (%s) אינו מאתר הכנסת או gov.il: %s"
                            % (i + 1, src.get("instrument") or "ללא שם", host(src.get("url", "")) or "אין קישור"))
            f.append("אינו מקור רשמי")
        if not src.get("verified"):
            f.append("טעון אימות")
        if src.get("effect") and src["effect"] not in LAW_EFFECTS:
            f.append("סוג השפעה לא מוכר")
        flags["law"].append(f)

    st = research.get("structures") or []
    if len(st) > MAX_STRUCTURES:
        blocking.append("%d מקורות מבנה. המקסימום %d: מעבר לזה אין תוספת, רק רעש." % (len(st), MAX_STRUCTURES))
    elif len(st) < MIN_STRUCTURES:
        notes.append("נמצאו רק %d מקורות מבנה, פחות מ-%d. המבנה נשען בעיקר על הידע על סוג ההסכם."
                     % (len(st), MIN_STRUCTURES))

    seen, saturated_at = set(), None
    for i, src in enumerate(st):
        f = []
        typ = src.get("source_type") or "אחר"
        topics = set(t.strip() for t in (src.get("topics") or []) if t and t.strip())
        new = topics - seen
        seen |= topics
        if i >= MIN_STRUCTURES and not new and saturated_at is None:
            saturated_at = i
        if typ not in VERBATIM_OK:
            f.append("מבנה בלבד, בלי העתקת נוסח")
        else:
            f.append("מותר כלשונו, בציון המקור")
        if typ == "ממשלתי-מכרז" or (is_government(src.get("url", "")) and typ not in VERBATIM_OK):
            f.append("נכתב לטובת המדינה כלקוח")
            if role and "ספק" in role:
                notes.append("\"%s\" הוא נוסח ממשלתי שנכתב לטובת המדינה כלקוח, והחברה היא הספק. "
                             "הוא משמש לעיון בלבד." % (src.get("title") or "מקור %d" % (i + 1)))
        if src.get("governing_law") and "ישראל" not in src["governing_law"]:
            f.append("דין זר: מוסד שאינו קיים בדין הישראלי מסומן")
        if not new and i > 0:
            f.append("לא הוסיף נושא חדש")
        flags["structures"].append(f)
    if saturated_at is not None:
        extra = len(st) - saturated_at - 1
        notes.append("רוויה: מקור %d לא הוסיף אף נושא חדש.%s"
                     % (saturated_at + 1, (" %d מקורות אחריו מיותרים." % extra) if extra > 0 else ""))
    if research.get("case_law_sensitive"):
        notes.append("סעיפים שתוקפם נקבע בפסיקה, ויסומנו בטיוטה \"טעון בדיקת פסיקה\": "
                     + ", ".join(research["case_law_sensitive"]))
    if research.get("foreign_institutions"):
        notes.append("מוסדות משפטיים זרים שדורשים התאמה לדין הישראלי: "
                     + ", ".join(research["foreign_institutions"]))
    if not research.get("consent_at"):
        blocking.append("אין תיעוד לאישור המשתמש לצאת למחקר (consent_at). מחקר נעשה רק אחרי אישור.")
    return blocking, flags, notes
