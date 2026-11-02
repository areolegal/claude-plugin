# -*- coding: utf-8 -*-
"""כללי מצב 4 של רכיב הניסוח, כקוד ולא כהמלצה.

מצב 4: ללקוח אין טיוטה, הסכמים או פלייבוק מהסוג המבוקש. **זה המקום היחיד במערכת
שבו רכיב הניסוח יוצא לרשת**, ורק אחרי שהמשתמש בחר את היקף העבודה:

  agreements  איסוף 10 עד 15 הסכמים מפורסמים שמייצגים את הפוזיציה של המשתמש
  research    מחקר רגולטורי בשכבות, ממאגר המקורות המאושרים בלבד
  both        שניהם

מקורות הדין (איסור קשיח, לא סימון): **הרשימה הסגורה המשותפת, `מקורות-מאושרים.json`** (areo-shared), אותה
רשימה שבונה הפלייבוק ומעריך הסיכונים טוענים (risk.validate_register.approved_domains בספרייה המשותפת): רק מקור
שהסטטוס שלו approved, ומקור עם allowed_paths גם בנתיב. הקובץ נשמר לדיסק ועובר ב-`--approved-sources`, או
במשתנה הסביבה AREO_APPROVED_SOURCES. כך גם דין זר נחקר, במקורות הרשמיים שברשימה. **בלי קובץ אין מחקר
רגולטורי**: ApprovedSourcesMissing, והסקריפטים מסרבים בקוד 2. אין רשימת נפילה בקוד.
  הכללים זהים לספרייה המשותפת (risk.validate_register.approved_domains ו-domain_ok, common.net.rule_matches),
  וכשהיא ניתנת לייבוא משתמשים בה עצמה: include_subdomains (תת-דומיין רק כשהמקור מתיר; www תמיד), include_hosts,
  allowed_paths בגבול מקטע, דף מאושר (pages) ככלל משלו, נתיב עם שאילתה (כל המפתחות שבכלל חייבים להופיע בכתובת),
  ומקור עם הגבלת שימוש בלי נתיבים נדחה, אלא אם restriction_kind הוא "content".
  **אין פסיקה בכלל**: לא מנבו ולא מאתרי בתי המשפט, גם כשהם ברשימה. common.case_law.case_law_url מהספרייה
  המשותפת כשהיא ניתנת לייבוא, ואחריה הבדיקה המקומית; ומה שהרשימה מסמנת case_law_only חסום.
  כל מקור אחר, כולל אתרי משרדי עורכי דין, מאמרים ובלוגים, אינו נאסף ואינו מוצג.

הסכמים מייצגים: האיסור על אתרי משרדי עורכי דין ועל מאגרים מסחריים חל גם כשמחפשים נוסח (hard-rules.md
המשותף, "מקורות לנוסחים"). source_type כזה, או כתובת של מאגר מסחרי, חוסמים.

הבדיקות מחזירות blocking (עוצר את השלב), flags (סימון ליד מקור) ו-notes (הערות).
"""
import io
import json
import os
import posixpath
import re
import sys
from urllib.parse import parse_qsl, unquote, urlparse

# python -I: governing_law נטען מתיקיית הסקריפט
if os.path.dirname(os.path.abspath(__file__)) not in sys.path:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCOPES = {"agreements": "איסוף הסכמים מייצגים",
          "research": "מחקר רגולטורי בשכבות",
          "both": "איסוף הסכמים ומחקר רגולטורי"}

COURT_HOST_MARKERS = ("court.gov.il", "courts.", "curia.europa.eu", "supremecourt", "judiciary", "bailii.org",
                      "caselaw.", "canlii.org", "austlii.edu.au", "courtlistener.com", "tribunal")   # פסיקה אינה מקור
# מדור פסיקה באתר שמותר לחקיקה: בדיקה מקומית מינימלית, למקרה שהספרייה המשותפת (common.case_law) אינה זמינה
COURT_PATH_MARKERS = ("psika", "verdict", "judgment", "judgement", "/juri", "ecli", "celex:6", "celex%3a6",
                      "tribunal-decisions", "/cases/", "case-law", "caselaw")
try:                                   # הספרייה המשותפת, כשהסקריפט רץ מתוך החבילה (AREO_RT/lib)
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from areo_rt import ensure_lib
    ensure_lib()
    from common.case_law import case_law_url as _lib_case_law_url
except ImportError:                    # pragma: no cover
    _lib_case_law_url = None

# הרשימה המחייבת: מקורות-מאושרים.json המשותף (load_approved_sources). הנתיב: --approved-sources, ואחריו
# משתנה הסביבה, ואחריהם העותק שנארז בתוסף (lib/מקורות-מאושרים.json; אין הורדה מהשרת בזמן ריצה). אותו סדר
# ואותו שם משתנה כמו בספרייה המשותפת (risk.validate_register.sources_path), כדי שהגדרה אחת תשמש את כל הרכיבים
APPROVED_SOURCES_ENV = "AREO_APPROVED_SOURCES"
APPROVED_SOURCES_FILE = "מקורות-מאושרים.json"
# בלי הקובץ המשותף אין רשימה חלופית: המחקר הרגולטורי נעצר (קוד 2 בסקריפטים)
MISSING_SOURCES = ("רשימת המקורות המאושרים (מקורות-מאושרים.json) לא נטענה. אין מחקר רגולטורי בלעדיה. העותק נארז "
                   "בתוסף (lib/מקורות-מאושרים.json); כשהוא חסר או שנמסר נתיב אחר שאינו קיים, תקנו את הנתיב "
                   "ב---approved-sources.\nThe approved sources list (מקורות-מאושרים.json) was not loaded. There is "
                   "no regulatory research without it.")


def default_sources_path():
    """העותק שנארז בתוסף: <lib>/מקורות-מאושרים.json, דרך הספרייה המשותפת (areo_rt.areo_lib). None כשאין ספרייה."""
    try:
        from areo_rt import areo_lib
        lib = areo_lib()
    except ImportError:                # pragma: no cover
        lib = None
    return os.path.join(lib, APPROVED_SOURCES_FILE) if lib else None


class ApprovedSourcesMissing(Exception):
    """אין קובץ מקורות-מאושרים.json תקף. הסקריפטים מסרבים בקוד 2."""

NORM_RANKS = {1: "חקיקה ראשית", 2: "חקיקת משנה", 3: "הוראה מחייבת של רגולטור",
              4: "הנחיה או מדריך של רגולטור", 5: "עמדת סגל או שו\"ת", 6: "מקור בהליך"}
RANK_STATUS = {1: "מחייב", 2: "מחייב", 3: "מחייב", 4: "מנחה", 5: "מנחה", 6: "בהליך"}
MANDATORY_ALLOWED_RANKS = (1, 2, 3)
RECOMMENDED_RANKS = (4, 5)

MIN_AGREEMENTS, TARGET_AGREEMENTS, MAX_AGREEMENTS = 10, 10, 15
# סדר החיפוש להסכמים מייצגים. אתרי משרדי עורכי דין ומאגרים מסחריים אינם מקור גם לנוסח (hard-rules.md המשותף)
AGREEMENT_SOURCE_ORDER = ("רגולטור", "גוף ציבורי", "הליך תחרותי ציבורי", "דיווח פומבי", "אתר המפרסם", "אחר")
FORBIDDEN_AGREEMENT_SOURCES = ("משרד עורכי דין", "אתר משפטי", "מאגר מסחרי")
# מאגרים מסחריים מצרפים: לאיתור בלבד, ואת המסמך קוראים במקור המקורי. כתובת כזו אינה מקור להסכם
COMMERCIAL_REPOSITORY_HOSTS = ("lawinsider.com", "lawdepot.com", "rocketlawyer.com", "legalzoom.com",
                               "docracy.com", "legaltemplates.net", "contractstandards.com", "onecle.com")
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


_SOURCES_CACHE = {}

try:                                   # הכללים של הספרייה המשותפת, כשהיא ניתנת לייבוא
    from risk.validate_register import approved_domains as _lib_approved_domains  # noqa: E402
    from common.net import rule_matches as _lib_rule_matches  # noqa: E402
except ImportError:                    # pragma: no cover
    _lib_approved_domains = _lib_rule_matches = None


def _norm_dom(d):
    d = (d or "").strip().lower().split("://", 1)[-1].rstrip("/").rstrip(".")
    return d[4:] if d.startswith("www.") else d


def _src_rules(src):
    """כללי מקור אחד, כמו _src_rules בספרייה המשותפת: [] כשהמקור אינו approved, או כשיש לו הגבלת שימוש בלי
    נתיבים במכונה ובלי restriction_kind "content"."""
    dom, _, dpath = _norm_dom(src.get("domain")).partition("/")
    if src.get("status") != "approved" or not dom:
        return []
    paths = [x for x in (src.get("allowed_paths") or []) if (x or "").strip("/")]
    if dpath:
        paths = paths or ["/" + dpath]
    restricted = any((src.get(k) or "").strip() for k in src if k.startswith("usage_restriction"))
    kind = src.get("restriction_kind")
    if (restricted or kind == "paths") and not paths and kind != "content":
        return []
    base = ("" if src.get("include_subdomains") else "=") + dom
    rules = [base + "/" + x.strip().lstrip("/") for x in paths] or [base]
    rules += ["=" + _norm_dom(h) for h in src.get("include_hosts") or [] if _norm_dom(h)]
    return rules


def _page_rule(pg):
    """דף מאושר: הכתובת והנתיבים שמתחתיה, במארח עצמו, עם מזהי הגוף שבשאילתה (OfficeId, TopicId, Type)."""
    if pg.get("status") != "approved" or not pg.get("url"):
        return None
    sp = urlparse(pg["url"])
    host = _norm_dom(sp.hostname)
    if not host:
        return None
    keep = [kv for kv in sp.query.split("&") if re.match(r"(?i)(officeid|topicid|type)=", kv)]
    return "=" + host + (sp.path.rstrip("/") or "") + ("?" + "&".join(keep) if keep else "")


def _case_law_rules(data):
    """כללי דחייה ("!") מ-case_law_only: רשימה, {sources|domains} או {jurisdictions: [{sources}]}."""
    blk = (data or {}).get("case_law_only")
    if isinstance(blk, dict):
        items = list(blk.get("sources") or []) + list(blk.get("domains") or []) or \
            [x for j in blk.get("jurisdictions") or [] for x in (j.get("sources") or [])]
    else:
        items = list(blk or [])
    out = []
    for c in items:
        c = {"domain": c} if isinstance(c, str) else (c or {})
        dom = _norm_dom(c.get("domain"))
        if dom:
            paths = [x for x in (c.get("paths") or c.get("allowed_paths") or []) if (x or "").strip("/")]
            out += ["!" + dom + "/" + x.lstrip("/") for x in paths] or ["!" + dom]
    return out


def load_approved_sources(path=None):
    """(כללים, הנתיב שנקרא) מהקובץ המשותף מקורות-מאושרים.json, בתחביר של common.net.rule_matches: "dom",
    "=dom/path?key=val" ו-"!dom" (דחייה, case_law_only). path: הארגומנט, ואחריו משתנה הסביבה. בלי קובץ, או כשאינו
    נקרא: ((), None), והמחקר נעצר. בלי ארגומנט ובלי משתנה סביבה: העותק שבתוסף (default_sources_path)."""
    path = path or os.environ.get(APPROVED_SOURCES_ENV) or default_sources_path()
    if path in _SOURCES_CACHE:
        return _SOURCES_CACHE[path]
    out = ((), None)
    if path and os.path.isfile(path):
        if _lib_approved_domains:
            try:
                rules, used = _lib_approved_domains(path)
                out = (tuple(rules) + tuple(getattr(rules, "refuse", ())), used) if used else ((), None)
            except Exception:  # noqa: BLE001  הקובץ אינו נקרא: אין רשימה
                out = ((), None)
        else:
            try:
                with io.open(path, encoding="utf-8-sig") as fh:
                    data = json.load(fh)
                rules = []
                for j in data.get("jurisdictions") or []:
                    for src in j.get("sources") or []:
                        if isinstance(src, dict):
                            rules += _src_rules(src)
                    for pg in j.get("pages") or []:
                        r = _page_rule(pg) if isinstance(pg, dict) else None
                        if r:
                            rules.append(r)
                if rules:
                    out = (tuple(dict.fromkeys(rules + _case_law_rules(data))), path)
            except (OSError, ValueError, AttributeError):
                out = ((), None)
    _SOURCES_CACHE[path] = out
    return out


def require_approved_sources(path=None):
    """הכללים מהקובץ המשותף, או ApprovedSourcesMissing כשאין קובץ תקף."""
    rules, used = load_approved_sources(path)
    if not used:
        raise ApprovedSourcesMissing(MISSING_SOURCES)
    return rules


def _norm_path(path):
    p = unquote(path or "/").replace(chr(92), "/")
    p = posixpath.normpath("/" + p.lstrip("/"))
    p = re.sub(r"/+", "/", p)
    return ("/" if p in (".", "") else p).lower()


def _path_under(path, prefix, bounded=True):
    prefix = _norm_path(prefix).rstrip("/") or "/"
    if prefix == "/":
        return True
    return path.startswith(prefix) if not bounded else (path == prefix or path.startswith(prefix + "/"))


def rule_matches(url, rule):
    """כמו common.net.rule_matches: "=" בלי תתי-דומיינים, נתיב בגבול מקטע (בכלל "!" תחילית), וכל זוג key=value
    שבשאילתה של הכלל חייב להופיע בכתובת."""
    if _lib_rule_matches:
        return _lib_rule_matches(url, rule)
    rule = (rule or "").strip()
    neg = rule.startswith("!")
    rule = rule[1:] if neg else rule
    exact = rule.startswith("=")
    rule = rule[1:] if exact else rule
    rule = rule[2:] if rule.startswith("*.") else rule
    rule, _, rq = rule.partition("?")
    rh, _, rp = rule.partition("/")
    rh = rh.lower().strip(".")
    rh = rh[4:] if rh.startswith("www.") else rh
    try:
        u = urlparse(url or "")
        host = (u.hostname or "").lower().rstrip(".")
    except ValueError:
        return False
    if not host or not rh:
        return False
    if exact and host not in (rh, "www." + rh):
        return False
    if not exact and not (host == rh or host.endswith("." + rh)):
        return False
    if rp and not _path_under(_norm_path(u.path), "/" + rp, bounded=not neg):
        return False
    if rq:
        have = {(k.lower(), v.lower()) for k, v in parse_qsl(u.query, keep_blank_values=True)}
        if any((k.lower(), v.lower()) not in have for k, v in parse_qsl(rq, keep_blank_values=True)):
            return False
    return True


def case_law_source(url):
    """הסיבה כשהכתובת היא של בית משפט, מאגר פסיקה או מדור פסיקה; אחרת None. common.case_law מהספרייה
    המשותפת כשהיא ניתנת לייבוא; הבדיקה המקומית רצה תמיד אחריה, כרשת ביטחון."""
    if _lib_case_law_url:
        why = _lib_case_law_url(url)
        if why:
            return why
    host, _ = _parts(url)
    rest = (url or "").lower().split(host, 1)[-1] if host else ""     # הנתיב והשאילתה (CELEX:6... בשאילתה)
    if any(m in host for m in COURT_HOST_MARKERS) or any(m in rest for m in COURT_PATH_MARKERS):
        return "פסיקה אינה מקור במחקר הזה. פסיקה רק ממחבר פסיקה סגור שהלקוח חיבר (כלל 1.1)"
    return None


def law_source_problem(url, jurisdiction=None, approved_sources=None):
    """None כשהמקור מותר, אחרת הסיבה. זה המקום היחיד שמכריע אם מקור הוא מקור דין. ההכרעה מול הרשימה
    הסגורה המשותפת (load_approved_sources), בדומיין, בתת-דומיין ובנתיב, לכל דין. jurisdiction נשאר לתאימות;
    מקור רשמי ברשימה מותר לכל מדינה שבה. בלי קובץ: ApprovedSourcesMissing."""
    host, path = _parts(url)
    if not host:
        return "אין קישור"
    why = case_law_source(url)
    if why:
        return why
    rules = require_approved_sources(approved_sources)
    if any(r.startswith("!") and rule_matches(url, r) for r in rules):
        return "מסומן ברשימה המשותפת כמקור פסיקה בלבד (case_law_only): %s" % host
    if any(not r.startswith("!") and rule_matches(url, r) for r in rules):
        return None
    return "אינו ברשימת המקורות המאושרים (מקורות-מאושרים.json), בדומיין, בתת-דומיין או בנתיב: %s" % host


# מדינות האיחוד: מקור של האיחוד (EU) חל בהן, ואינו "דין זר" להסכם שכפוף לדין שלהן
EU_MEMBERS = ("AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV", "LT",
              "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE")


def applies_within(src_law, base_law):
    """True כשמקור בדין src_law חל בתוך הדין החל base_law: אותו דין, הדין הכלל-מדינתי (US להסכם בדין US-NY,
    GB להסכם בדין GB-EAW), או מקור של האיחוד להסכם בדין מדינה חברה."""
    import governing_law as GL
    s_, b = GL.code(src_law) or str(src_law or "").strip().upper(), GL.code(base_law)
    if not (s_ and b):
        return False
    country = b.split("-")[0]
    return s_ == b or s_ == country or (s_ == "EU" and country in EU_MEMBERS)


def agreement_source_problem(agreement):
    """None כשמקור ההסכם מותר, אחרת הסיבה: אתר משרד עורכי דין, אתר משפטי או מאגר מסחרי אינם מקור."""
    typ = (agreement.get("source_type") or "").strip()
    if typ in FORBIDDEN_AGREEMENT_SOURCES:
        return "מקור מסוג \"%s\" אינו מותר גם לנוסח (hard-rules.md המשותף, מקורות לנוסחים)" % typ
    host, _ = _parts(agreement.get("url"))
    if host and any(host == h or host.endswith("." + h) for h in COMMERCIAL_REPOSITORY_HOSTS):
        return "מאגר מסחרי (%s) משמש לאיתור בלבד; את ההסכם מצטטים מהמקור המקורי" % host
    return None


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


def check(research, stage="brief", approved_sources=None, inc_country=None):
    """stage: 'brief' לפני הצגת המחקר, 'draft' לפני ניסוח. אין שער אישור על המחקר (כלל 6): הלקוח נשאל שאלה רגילה, והניסוח אינו ממתין.
    approved_sources: מקורות-מאושרים.json שנשמר לדיסק; בלעדיו משתנה הסביבה. בלי קובץ, כשנבחר מחקר
    רגולטורי: ApprovedSourcesMissing (קוד 2 בסקריפטים).
    inc_country: מדינת ההתאגדות מהפרופיל, לסימון "דין זר" כשבמחקר לא נרשם הדין החל (jurisdiction)."""
    import governing_law as GL
    r = normalise(research)
    blocking, notes = [], []
    flags = {"law": [], "agreements": [], "mandatory": []}

    if r.get("scope") not in SCOPES:
        blocking.append("לא נבחר היקף העבודה (scope): agreements, research או both.")
    if not r.get("consent_at"):
        blocking.append("אין תיעוד לבקשה המפורשת של הלקוח לנסח מבחוץ (consent_at). ניסוח מבחוץ רק כשאין ללקוח פלייבוק ואין הסכמי טיוטה, והוא ביקש זאת במפורש.")
    if not (r.get("company_role") or "").strip():
        blocking.append("הפוזיציה של המשתמש (company_role) חסרה. היא נשאלת, ולעולם אינה מוסקת.")

    # ---- regulatory research
    law = r.get("law") or []
    if scope_has(r, "research"):
        if not law:
            blocking.append("נבחר מחקר רגולטורי, ואין אף מקור דין.")
        require_approved_sources(approved_sources)
        if not r.get("jurisdiction"):
            blocking.append("הדין החל (jurisdiction) לא נקבע. הוא נקבע לפני המחקר: מהמשתמש, מנייר הבית, או בשאלה "
                            "אחת עם המלצה לפי מדינת ההתאגדות שבפרופיל, והמחקר נערך בתוכו.")
        base_law = GL.code(r.get("jurisdiction")) or GL.code(inc_country)
        last_rank = 0
        for i, src in enumerate(law):
            f = []
            name = src.get("instrument") or "שורה %d" % (i + 1)
            problem = law_source_problem(src.get("url"), src.get("jurisdiction"), approved_sources)
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
            # הדין של המקור מול הדין החל של ההסכם (ובלעדיו מדינת ההתאגדות), ולא מול ישראל
            if not (src.get("jurisdiction") or "").strip():
                f.append("תחום שיפוט לא צוין")
            elif base_law and not applies_within(src.get("jurisdiction"), base_law):
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
        # ההערה נכתבת בסיכום המחקר: בלי המילה "פסיקה" (areo-hard-rules 1.1, 3.5)
        notes.append("המחקר מוגבל למאגר המקורות המאושרים. נקודה שאין לה מקור מורשה מסומנת: "
                     "AREO לא מצאה מקור מורשה לנקודה זו.")
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
            src_problem = agreement_source_problem(a)
            if src_problem:
                blocking.append("הסכם %d (%s): %s." % (i + 1, title, src_problem))
            typ = a.get("source_type") or "אחר"
            if typ == "אחר":
                f.append("מקור לא מסווג: ודאו שאינו אתר משרד עורכי דין או מאגר מסחרי")
            f.append("מותר כלשונו, בציון המקור" if typ in VERBATIM_OK else "מבנה, נושאים ועמדות בלבד")
            if typ == "הליך תחרותי ציבורי":
                f.append("נכתב לטובת הגוף הציבורי המזמין")
                f.append("לעיון בלבד, אלא אם החברה היא הגוף המזמין")
            unknown = [x for x in (a.get("missing_mandatory") or []) if mand_ids and x not in mand_ids]
            if unknown:
                f.append("סעיפי חובה לא מוכרים: " + ", ".join(unknown))
            flags["agreements"].append(f)

    return blocking, flags, notes


def approved_mandatory(research):
    return [m for m in (normalise(research).get("mandatory_clauses") or []) if m.get("status") != "הוסר"]


def approved_agreements(research):
    r = normalise(research)
    removed = set(str(x) for x in (r.get("approvals") or {}).get("removed_agreements") or [])
    return [a for a in (r.get("agreements") or []) if str(a.get("no")) not in removed]


MONTHS_EN = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
             "November", "December")


def display_date(v, lang="he"):
    """ISO בקובץ; בתצוגה לפי שפת התוצר (כלל 3.6): יום.חודש.שנה בעברית, "3 April 2027" באנגלית.
    ערך שלא אותר, או שאינו ISO, מוצג כפי שהוא."""
    s = (v or "").strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and s[:4].isdigit() and s[5:7].isdigit() and s[8:10].isdigit():
        y, m, d = s[:4], int(s[5:7]), int(s[8:10])
        if 1 <= m <= 12:
            if str(lang or "he")[:2].lower() == "en":
                return "%d %s %s" % (d, MONTHS_EN[m - 1], y)
            return "%d.%d.%s" % (d, m, y)
    return s or NOT_FOUND


# --------------------------------------------------------------------------- בדיקת כתובת אחת, בלי לטעון את הרשימה
def lookup_source(url, path=None):
    """הרשומה של כתובת אחת ברשימת המקורות המאושרים, מהדיסק: {"status": approved|case_law_only|pending|not_approved|
    not_on_list|no_list, "entry": {...} כשיש}. המודל אינו קורא את הרשימה (157K תווים): הוא שואל את הקוד על כתובת אחת.
    common.approved_sources מהספרייה המשותפת כשהיא ניתנת לייבוא; אחרת הבדיקה המקומית, שמחזירה רק את הכלל שהתאים."""
    try:
        from common.approved_sources import lookup as _lib_lookup
    except ImportError:                # pragma: no cover
        _lib_lookup = None
    if _lib_lookup:
        return _lib_lookup(url, path)
    host, _p = _parts(url)
    res = {"url": url, "host": host}
    rules, used = load_approved_sources(path)
    if not used:
        res.update(status="no_list", reason=MISSING_SOURCES.split("\n")[0])
        return res
    why = case_law_source(url)
    if why or any(r.startswith("!") and rule_matches(url, r) for r in rules):
        res.update(status="case_law_only", reason=why or "case_law_only")
        return res
    hit = next((r for r in rules if not r.startswith("!") and rule_matches(url, r)), None)
    if hit:
        res.update(status="approved", entry={"rule": hit})
    else:
        res.update(status="not_on_list", reason="אינו ברשימת המקורות המאושרים: %s" % host)
    return res


def main(argv=None):
    import argparse
    sys.dont_write_bytecode = True
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    ap = argparse.ArgumentParser(description="כללי המקורות של הניסוח מבחוץ")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lk = sub.add_parser("lookup", help="הרשומה של כתובת אחת ברשימת המקורות המאושרים, בלי לקרוא את הרשימה")
    lk.add_argument("--url", required=True)
    lk.add_argument("--approved-sources", help="מקורות-מאושרים.json (ברירת מחדל: AREO_APPROVED_SOURCES, ואחריו העותק "
                                               "שבתוסף, lib/מקורות-מאושרים.json)")
    a = ap.parse_args(argv)
    res = lookup_source(a.url, a.approved_sources)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0 if res["status"] == "approved" else (2 if res["status"] == "no_list" else 1)


if __name__ == "__main__":
    sys.exit(main())
