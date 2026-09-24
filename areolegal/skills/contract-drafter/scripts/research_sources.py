# -*- coding: utf-8 -*-
"""כללי מצב 4 של רכיב הניסוח, כקוד ולא כהמלצה.

מצב 4: ללקוח אין טיוטה, הסכמים או פלייבוק מהסוג המבוקש. **זה המקום היחיד במערכת
שבו רכיב הניסוח יוצא לרשת**, ורק אחרי שהמשתמש בחר את היקף העבודה:

  agreements  איסוף 10 עד 15 הסכמים מפורסמים שמייצגים את הפוזיציה של המשתמש
  research    מחקר רגולטורי בשכבות, ממקורות רשמיים בלבד
  both        שניהם

מקורות הדין (איסור קשיח, לא סימון):
  ישראל  gov.il וכל תת-דומיין שלו, כולל אתר הכנסת; nevo.co.il בנתיבי חקיקה בלבד.
  חו"ל   רק דומיינים ממשלתיים רשמיים מהרשימה הסגורה FOREIGN_OFFICIAL_DOMAINS.
  **אין פסיקה בכלל**: לא מנבו ולא מאתרי בתי המשפט, גם כשהם תחת gov.il.
  כל מקור אחר, כולל אתרי משרדי עורכי דין, מאמרים ובלוגים, אינו נאסף ואינו מוצג.

הבדיקות מחזירות blocking (עוצר את השלב), flags (סימון ליד מקור) ו-notes (הערות).
"""
try:                                   # Python 3
    from urllib.parse import urlparse
except ImportError:                    # pragma: no cover
    from urlparse import urlparse

SCOPES = {"agreements": "איסוף הסכמים מייצגים",
          "research": "מחקר רגולטורי בשכבות",
          "both": "איסוף הסכמים ומחקר רגולטורי"}

ISRAELI_OFFICIAL_SUFFIX = "gov.il"                 # כולל knesset.gov.il ותת-דומיינים
NEVO_HOST = "nevo.co.il"
NEVO_ALLOWED_PATHS = ("/law_html/",)               # חקיקה בלבד. אין פסיקה בכלל
COURT_HOST_MARKERS = ("court.gov.il",)             # פסיקה אינה מקור, גם תחת gov.il

# רשימה סגורה. הוספה רק בהחלטת מוצר, לא בשיקול דעת בזמן ריצה.
# ערך שמתחיל בנקודה הוא סיומת; אחר הוא דומיין מדויק או כל תת-דומיין שלו.
FOREIGN_OFFICIAL_DOMAINS = {
    "US": (".gov",),
    "EU": ("eur-lex.europa.eu", "europa.eu"),
    "UK": ("legislation.gov.uk", ".gov.uk"),
    "DE": ("gesetze-im-internet.de", ".bund.de"),
    "FR": ("legifrance.gouv.fr", ".gouv.fr"),
    "CA": ("laws-lois.justice.gc.ca", ".gc.ca"),
    "AU": ("legislation.gov.au", ".gov.au"),
    "PT": ("dre.pt", ".gov.pt"),
}

NORM_RANKS = {1: "חקיקה ראשית", 2: "חקיקת משנה", 3: "הוראה מחייבת של רגולטור",
              4: "הנחיה או מדריך של רגולטור", 5: "עמדת סגל או שו\"ת", 6: "מקור בהליך"}
RANK_STATUS = {1: "מחייב", 2: "מחייב", 3: "מחייב", 4: "מנחה", 5: "מנחה", 6: "בהליך"}
MANDATORY_ALLOWED_RANKS = (1, 2, 3)
RECOMMENDED_RANKS = (4, 5)

MIN_AGREEMENTS, TARGET_AGREEMENTS, MAX_AGREEMENTS = 10, 10, 15
AGREEMENT_SOURCE_ORDER = ("אתר משפטי", "משרד עורכי דין", "רגולטור", "גוף ציבורי",
                          "ממשלתי-מכרז", "דיווח פומבי", "אחר")
VERBATIM_OK = ("רגולטור", "גוף ציבורי")
ORIENTATIONS = ("לטובת הפוזיציה", "מאוזן", "נגד הפוזיציה")
NOT_FOUND = "[לא אותר]"


def _parts(url):
    try:
        u = urlparse(url or "")
        return (u.hostname or "").lower(), (u.path or "")
    except Exception:
        return "", ""


def _host_matches(host, entry):
    if entry.startswith("."):
        return host.endswith(entry)
    return host == entry or host.endswith("." + entry)


def law_source_problem(url, jurisdiction="IL"):
    """None כשהמקור מותר, אחרת הסיבה. זה המקום היחיד שמכריע אם מקור הוא מקור דין."""
    host, path = _parts(url)
    if not host:
        return "אין קישור"
    if any(m in host for m in COURT_HOST_MARKERS):
        return "פסיקה אינה מקור במחקר הזה"
    code = (jurisdiction or "IL").upper()
    if code == "IL":
        if host == ISRAELI_OFFICIAL_SUFFIX or host.endswith("." + ISRAELI_OFFICIAL_SUFFIX):
            return None
        if host == NEVO_HOST or host.endswith("." + NEVO_HOST):
            if any(path.startswith(p) for p in NEVO_ALLOWED_PATHS):
                return None
            return "בנבו מותרים נתיבי חקיקה בלבד (%s)" % path
        return "אינו gov.il, אתר הכנסת או נבו בנתיב חקיקה: %s" % host
    allowed = FOREIGN_OFFICIAL_DOMAINS.get(code)
    if not allowed:
        return "אין רשימת אתרים רשמיים למדינה %s" % code
    if any(_host_matches(host, e) for e in allowed):
        return None
    return "אינו אתר ממשלתי רשמי של %s: %s" % (code, host)


def normalise(research):
    """קובץ מחקר בפורמט הקודם (structures, בלי scope) נקרא בלי לאבד נתונים."""
    r = dict(research)
    legacy = "structures" in r
    if "agreements" not in r and r.get("structures"):
        r["agreements"] = [dict(x, no=i + 1) for i, x in enumerate(r["structures"])]
    # The scope is the user's explicit choice. It is inferred only for a file written in
    # the old format, which had no such field; a current file without it is refused.
    if legacy and not r.get("scope"):
        has_a, has_r = bool(r.get("agreements")), bool(r.get("law"))
        r["scope"] = "both" if (has_a and has_r) else ("agreements" if has_a else ("research" if has_r else ""))
    r.setdefault("approvals", {})
    return r


def scope_has(research, part):
    s = research.get("scope")
    return s == "both" or s == part


def check(research, stage="brief"):
    """stage: 'brief' לפני הצגת המחקר, 'draft' לפני ניסוח (דורש גם את האישורים)."""
    r = normalise(research)
    blocking, notes = [], []
    flags = {"law": [], "agreements": [], "mandatory": []}

    if r.get("scope") not in SCOPES:
        blocking.append("לא נבחר היקף העבודה (scope): agreements, research או both.")
    if not r.get("consent_at"):
        blocking.append("אין תיעוד לאישור המשתמש לצאת לרשת (consent_at). היציאה לרשת רק אחרי בחירה.")
    if not (r.get("company_role") or "").strip():
        blocking.append("הפוזיציה של המשתמש (company_role) חסרה. היא נשאלת, ולעולם אינה מוסקת.")

    # ---- regulatory research
    law = r.get("law") or []
    if scope_has(r, "research"):
        if not law:
            blocking.append("נבחר מחקר רגולטורי, ואין אף מקור דין.")
        if not r.get("jurisdiction"):
            blocking.append("הדין החל (jurisdiction) לא נקבע. הוא עולה מהמחקר, ונרשם לפני הצגתו.")
        last_rank = 0
        for i, src in enumerate(law):
            f = []
            name = src.get("instrument") or "שורה %d" % (i + 1)
            problem = law_source_problem(src.get("url"), src.get("jurisdiction") or "IL")
            if problem:
                blocking.append("מקור דין %d (%s): %s" % (i + 1, name, problem))
                f.append("מקור אסור")
            rank = src.get("rank")
            if rank not in NORM_RANKS:
                blocking.append("מקור דין %d (%s): חסר דרג במדרג הנורמטיבי (1 עד 6)." % (i + 1, name))
            else:
                if rank < last_rank:
                    blocking.append("השורות אינן ממוינות לפי המדרג: מקור %d בדרג %d אחרי דרג %d."
                                    % (i + 1, rank, last_rank))
                last_rank = max(last_rank, rank)
            if not src.get("verified"):
                f.append("טעון אימות")
            if (src.get("jurisdiction") or "IL").upper() != "IL":
                f.append("דין זר")
            for k in ("published_original", "published_last"):
                if src.get(k) in (None, "", NOT_FOUND):
                    f.append("תאריך לא אותר")
                    break
            flags["law"].append(f)
        rows = {src.get("row", i + 1): src for i, src in enumerate(law)}
        for m in r.get("mandatory_clauses") or []:
            f = []
            src = rows.get(m.get("source_row"))
            cid = m.get("clause_id") or "?"
            if src is None:
                blocking.append("סעיף חובה %s: אין שורת מקור %s במחקר." % (cid, m.get("source_row")))
            else:
                if not src.get("verified"):
                    blocking.append("סעיף חובה %s נשען על מקור שלא אומת (שורה %s)." % (cid, m.get("source_row")))
                if src.get("rank") not in MANDATORY_ALLOWED_RANKS:
                    blocking.append("סעיף חובה %s נשען על מקור בדרג %s. סעיף חובה רק מדרגים 1 עד 3; "
                                    "מדרגים 4 ו-5 נגזר סעיף מומלץ." % (cid, src.get("rank")))
            flags["mandatory"].append(f)
        derived = {m.get("source_row") for m in (r.get("mandatory_clauses") or [])}
        for i, src in enumerate(law):
            row = src.get("row", i + 1)
            if src.get("mandatory") and src.get("verified") and src.get("rank") in MANDATORY_ALLOWED_RANKS \
                    and row not in derived:
                blocking.append("מקור %d (%s) סומן כמחייב סעיף חובה, ולא נגזר ממנו סעיף חובה."
                                % (i + 1, src.get("instrument") or ""))
        if r.get("layers_checked"):
            notes.append("שכבות שנבדקו: " + ", ".join(r["layers_checked"]))
        notes.append("המחקר מוגבל למקורות רשמיים ואינו מכסה פסיקה. סעיפים שתוקפם נקבע בפסיקה "
                     "מסומנים בטיוטה \"טעון בדיקת פסיקה\".")
    elif law:
        notes.append("נבחר איסוף הסכמים בלבד, ולכן מקורות הדין שבקובץ אינם חלק מהתוצר.")

    # ---- representative agreements
    ags = r.get("agreements") or []
    if scope_has(r, "agreements"):
        if len(ags) > MAX_AGREEMENTS:
            blocking.append("%d הסכמים. התקרה היא %d." % (len(ags), MAX_AGREEMENTS))
        elif len(ags) < MIN_AGREEMENTS:
            notes.append("נמצאו %d הסכמים רלוונטיים, פחות מ-%d.%s" % (
                len(ags), MIN_AGREEMENTS,
                (" הסיבה: " + r["agreements_shortfall_reason"]) if r.get("agreements_shortfall_reason") else ""))
        role = (r.get("company_role") or "")
        mand_ids = {m.get("clause_id") for m in (r.get("mandatory_clauses") or [])}
        for i, a in enumerate(ags):
            f = []
            title = a.get("title") or "הסכם %d" % (i + 1)
            host, _ = _parts(a.get("url"))
            if not host:
                blocking.append("הסכם %d (%s) בלי קישור." % (i + 1, title))
            o = a.get("orientation")
            if o not in ORIENTATIONS:
                blocking.append("הסכם %d (%s): חסר כיוון ביחס לפוזיציה." % (i + 1, title))
            elif o == "נגד הפוזיציה":
                blocking.append("הסכם %d (%s) מסווג \"נגד הפוזיציה\" ואינו נכלל." % (i + 1, title))
            if o in ORIENTATIONS and not (a.get("orientation_reason") or "").strip():
                f.append("חסר נימוק לכיוון")
            typ = a.get("source_type") or "אחר"
            f.append("מותר כלשונו, בציון המקור" if typ in VERBATIM_OK else "מבנה, נושאים ועמדות בלבד")
            if typ == "ממשלתי-מכרז":
                f.append("נכתב לטובת המדינה כלקוח")
                if "ספק" in role:
                    f.append("לעיון בלבד")
            unknown = [x for x in (a.get("missing_mandatory") or []) if mand_ids and x not in mand_ids]
            if unknown:
                f.append("סעיפי חובה לא מוכרים: " + ", ".join(unknown))
            flags["agreements"].append(f)

    # ---- approvals, before drafting
    if stage == "draft":
        ap = r.get("approvals") or {}
        if scope_has(r, "research") and not ap.get("research_at"):
            blocking.append("אין אישור של המשתמש למחקר הרגולטורי ולסעיפי החובה (approvals.research_at).")
        if scope_has(r, "agreements") and not ap.get("agreements_at"):
            blocking.append("אין אישור של המשתמש להסכמים (approvals.agreements_at).")
    return blocking, flags, notes


def approved_mandatory(research):
    return [m for m in (normalise(research).get("mandatory_clauses") or []) if m.get("status") == "מאושר"]


def approved_agreements(research):
    r = normalise(research)
    removed = set(str(x) for x in (r.get("approvals") or {}).get("removed_agreements") or [])
    return [a for a in (r.get("agreements") or []) if str(a.get("no")) not in removed]


def display_date(v):
    """ISO בקובץ, יום.חודש.שנה בתצוגה. ערך שלא אותר מוצג כפי שהוא."""
    s = (v or "").strip()
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        y, m, d = s.split("-")
        return "%d.%d.%s" % (int(d), int(m), y)
    return s or NOT_FOUND
